from odoo import models, api


class SurveyDashboard(models.AbstractModel):

    _name = 'survey.dashboard'
    _description = 'Survey Dashboard'


    @api.model
    def get_dashboard_data(self):

        surveys = self.env[
            'survey.survey'
        ].search([])

        survey_data = []

        total_registered = 0
        total_completed = 0

        for survey in surveys:

            participations = self.env[
                'survey.user_input'
            ].search([
                ('survey_id', '=', survey.id)
            ])

            registered = len(
                participations
            )

            completed = len(
                participations.filtered(
                    lambda x:
                    x.state == 'done'
                )
            )

            total_registered += registered
            total_completed += completed

            engagement = 0

            if registered:

                engagement = round(
                    (
                        completed /
                        registered
                    ) * 100,
                    2
                )


            items = survey.question_and_page_ids.sorted(
                key=lambda x: x.sequence
            )

            current_section = False

            questions = self.env[
                'survey.question'
            ]

            sections = []


            for rec in items:

                if rec.is_page:

                    if current_section:

                        response_count = self.env[
                            'survey.user_input.line'
                        ].search_count([

                            (
                                'question_id',
                                'in',
                                questions.ids
                            )

                        ])

                        possible = (
                            registered *
                            len(
                                questions
                            )
                        )

                        section_engagement = 0

                        if possible:

                            section_engagement = round(
                                (
                                    response_count /
                                    possible
                                ) * 100,
                                2
                            )

                        sections.append({

                            'name':
                            current_section.title,

                            'questions':
                            len(
                                questions
                            ),

                            'responses':
                            response_count,

                            'engagement':
                            section_engagement

                        })

                    current_section = rec

                    questions = self.env[
                        'survey.question'
                    ]

                else:

                    questions |= rec



            if current_section:

                response_count = self.env[
                    'survey.user_input.line'
                ].search_count([

                    (
                        'question_id',
                        'in',
                        questions.ids
                    )

                ])


                possible = (
                    registered *
                    len(
                        questions
                    )
                )


                section_engagement = 0

                if possible:

                    section_engagement = round(
                        (
                            response_count /
                            possible
                        ) * 100,
                        2
                    )

                sections.append({

                    'name':
                    current_section.title,

                    'questions':
                    len(
                        questions
                    ),

                    'responses':
                    response_count,

                    'engagement':
                    section_engagement

                })


            survey_data.append({

                'id':
                survey.id,

                'survey':
                survey.title,

                'registered':
                registered,

                'completed':
                completed,

                'pending':
                registered-completed,

                'engagement':
                engagement,

                'sections':
                sections

            })


        avg = 0

        if total_registered:

            avg = round(
                (
                    total_completed /
                    total_registered
                ) * 100,
                2
            )


        return {

            'cards': {

                'surveys':
                len(surveys),

                'registered':
                total_registered,

                'completed':
                total_completed,

                'engagement':
                avg
            },

            'surveys':
            survey_data

        }