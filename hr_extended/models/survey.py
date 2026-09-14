from odoo import fields, models,api, Command,_

class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def _get_default_question_commands(self):
        """Create default survey sections based on survey_category_id
        and put the default questions under their respective sections.
        """

        default_questions = self.env['survey.question'].search(
            [
                ('survey_id', '=', False),
                ('is_default_question', '=', True),
                ('is_page', '=', False),
            ],
            order='survey_category_id, sequence, id',
        )

        commands = []

        # Group questions by category
        categories = {}

        for question in default_questions:
            category = question.survey_category_id

            if category:
                categories.setdefault(category.id, {
                    'category': category,
                    'questions': [],
                })

                categories[category.id]['questions'].append(question)

            else:
                # Questions without category
                categories.setdefault(False, {
                    'category': False,
                    'questions': [],
                })

                categories[False]['questions'].append(question)

        sequence = 10

        # ---------------------------------------------------------
        # CREATE SECTIONS CATEGORY-WISE
        # ---------------------------------------------------------

        for category_data in categories.values():

            category = category_data['category']
            questions = category_data['questions']

            # -----------------------------------------------------
            # SECTION
            # -----------------------------------------------------

            if category:

                section_vals = {
                    'title': category.name,
                    'sequence': sequence,
                    'is_page': True,
                    'survey_category_id': category.id,
                    'is_default_question': False,
                }

                commands.append(
                    Command.create(section_vals)
                )

                sequence += 10

            # -----------------------------------------------------
            # QUESTIONS
            # -----------------------------------------------------

            for default_question in questions:

                question_vals = {
                    'title': default_question.title,
                    'sequence': sequence,
                    'is_page': False,
                    'survey_category_id': (
                        default_question.survey_category_id.id
                        if default_question.survey_category_id
                        else False
                    ),
                    'question_type': default_question.question_type,
                    'constr_mandatory': default_question.constr_mandatory,
                    'description': default_question.description,
                    'is_default_question': False,
                }

                # -------------------------------------------------
                # ANSWERS
                # -------------------------------------------------

                answer_commands = []

                for answer in default_question.suggested_answer_ids.sorted(
                    key=lambda a: (a.sequence, a.id)
                ):

                    answer_commands.append(
                        Command.create({
                            'value': answer.value,
                            'sequence': answer.sequence,
                            'is_correct': answer.is_correct,
                            'answer_score': answer.answer_score,
                        })
                    )

                if answer_commands:
                    question_vals['suggested_answer_ids'] = answer_commands

                commands.append(
                    Command.create(question_vals)
                )

                sequence += 10

        return commands

    @api.model
    def default_get(self, fields_list):

        values = super().default_get(fields_list)

        # Only prepare questions when the Survey form is asking for them.
        if 'question_and_page_ids' in fields_list:

            if not self.env.context.get(
                'skip_default_survey_questions'
            ):

                values['question_and_page_ids'] = (
                    self._get_default_question_commands()
                )

        return values


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    is_default_question = fields.Boolean(
        string='Default Question',
        default=False,
        copy=False,
        help='Marks this question as a reusable default question. '
             'Default questions are copied automatically to newly created surveys.'
    )