# thanks ivy
import logging
import os
import re
import ast
import json
import time

from collections import defaultdict

from src.ed_helper import EdHelper

from typing import (
    List, Optional, Callable, Dict
)

from src.constants import (
    PROGRESS_UPDATE_MULTIPLE
)

class DeductionsRegex:
    GENERAL_DEDUCTIONS_PATTERN = re.compile(r'.*General Deductions:\s*')
    CREATIVE_EXTENSION_PATTERN = re.compile(r'Creative Extension:\s*')
    TESTING_REFLECTION_PATTERN = re.compile(r'Testing/Reflection:.*')

ED_TESTING = "https://us.edstem.org/api/challenges/submissions/{submission_id}/line_comments"


class DeductionsChecker:
    @staticmethod
    async def check_deductions(
        ed_helper: EdHelper,
        url: str, file_name: str,
        template: Optional[bool] = False,
        progress_bar_update: Optional[Callable[[int, int], None]] = None,
        ferpa: Optional[bool] = True
    ) -> Dict[str, int]:
        # Get List[str] where each element is a string of one student's
        # final feedback box
        # url = ED_TESTING
        feedback_list = await DeductionsChecker._pull_inlines(ed_helper, url, template, progress_bar_update, ferpa)
        # feedback_list = await DeductionsChecker._pull_submissions(ed_helper, url, template, progress_bar_update, ferpa)

        # Parse final feedback box List[str]s into a List where each
        # element is a string representation a deduction bullet point

        # Group all deduction lines into a Dict
        
        return
    
    @staticmethod
    async def _pull_inlines(
        ed_helper: EdHelper,
        url: str,
        template: Optional[bool] = False,
        progress_bar_update: Optional[Callable[[int, int], None]] = None,
        ferpa: Optional[bool] = True
    ) -> List[str]:
        attempt_slide = EdHelper.is_overall_submission_link(url)

        # Get the challenge id for the assignment
        ids = EdHelper.get_ids(url)

        #remove?
        lesson_id, slide_id = ids[1], ids[2]

        challenge_id = ed_helper.get_slide(url)['challenge_id']


        users = None
        if True:
            slide = ed_helper.get_slide(url)
            users = [user for user
                     in ed_helper.get_challenge_users(slide['challenge_id'])
                     if True]
                    #  if user['course_role'] == 'student']

        # grab all submissions using their submission and challenge id
        user_ids = [user['id'] for user in users] # store user ids needed for get_challenge_submissions - challenge_id from above
        challenge_subs = [ed_helper.get_challenge_submissions(id, challenge_id) for id in user_ids ]
        test = [entry['id'] for group in challenge_subs for entry in group]

        # store all feedback in a dict (potentially need to run this on all assignments and then make a new dcit to cross reference for everything?)
        all_feedback_hopefully = {}
        all_feedback_html = ""

        # lets see how long this takes to run
        # start = time.time()

        # for every student for all student feedback, get their inline feedback and store into a file
        for (sub_id) in test:
            json_return = ed_helper.get_inline_submissions(sub_id)["comments"]
            # skip if ungraded
            if (json_return is None):
                continue

            # for every inline deduction for the student grab all the info and separate header and body for (header -> body) dict
            for (full_comment) in json_return:
                # grab only inline from json junk
                inline_comment = full_comment["content"]


                # get all the feedback separated per deduction for all the students
                all_feedback_html += str(inline_comment)
                all_feedback_html += "\n----------------------------------------------------------------------------------------------------------------\n"
                with open("demofile.txt", "a") as f:
                    f.write(str(inline_comment))

                # below to next inline is commented out but is the dict of deduction header to body
                # kill_after = re.sub(r"</.*>", "", inline_comment)
                # deduction_header = re.sub(r"<.*>", "", kill_after)
                # index = inline_comment.find(deduction_header) + len(deduction_header)
                # removed_header = inline_comment[index:]
                # comment_body = re.sub(r"<[^>]*>", "", removed_header)
                # # need to find the infomation afterwards now to add to dict
                # all_feedback_hopefully[deduction_header] = comment_body
                #comment ends here

        # end time it takes to run
        # end = time.time()
        #with open("demofile.txt", "a") as f:
        # f.write(str(inline_comment))

        raise Exception(str(all_feedback_html))

        #NEW SPOT RIGHT HERE
        # TODO create a map where the keys are the titles (bolded parts of an annotation) and the values are the written comments in the final
        #   submission box
        # might need to store the dict so that it can be referenced instead of creating a new one each time (majority of the runtime)
        # end goal - compare to the overall feedback box (need to write method to grab all overall with smth to id the sub)
        #               and see if for each overall feedback, there is a matching inline deduction somewhere in sub

    @staticmethod
    async def _pull_submissions(
        ed_helper: EdHelper,
        url: str,
        template: Optional[bool] = False,
        progress_bar_update: Optional[Callable[[int, int], None]] = None,
        ferpa: Optional[bool] = True
    ) -> List[str]:
        """
        Pulls final submission slides of all student submissions and creates
        a List with all the contents of each feedback box.

        Params: 'ed_helper' - A properly initialized EdHelper object with API
                              access to the ed assignment
                'url' - The ed assignment url
                'template' - Whether or not the grading template is expected,
                             default False
                'progress_bar_update' - A function to call with incremental
                                        values that updates a user-viewable
                                        progress bar, default None
                'ferpa' - Whether or not to censor student emails from links,
                          default True
        Returns: A dictionary mapping (TA | link) -> (link, fixes) for all
                 assignment that had incorrect formatting and a List of links
                 to student assignments not found in the grading spreadsheet
        """
        attempt_slide = EdHelper.is_overall_submission_link(url)

        # Get the challenge id for the assignment
        ids = EdHelper.get_ids(url)
        lesson_id, slide_id = ids[1], ids[2]
        challenge_id = (ed_helper.get_slide(url)['challenge_id']
                        if not attempt_slide else None)

        # Get user/challenge information
        users, num_criteria, rubric = None, None, None
        if not attempt_slide:
            users = [(user['id'], None, user['tutorial'], None)
                     for user in ed_helper.get_challenge_users(challenge_id)
                     if user['course_role'] == "student"]

            challenge = ed_helper.get_challenge(challenge_id)
            num_criteria = len(challenge['settings']['criteria'])
        else:
            users = [(attempt['user_id'], attempt['email'],
                      attempt['tutorial'], attempt['sourced_id'])
                     for attempt in ed_helper.get_attempt_results(lesson_id)
                     if attempt['course_role'] == 'student']

            lesson = ed_helper.get_lesson(lesson_id)
            rubric = ed_helper.get_rubric(ed_helper.get_rubric_id(slide_id))
            num_criteria = len(rubric['sections'])

        feedback_list, count = [], 0

        for (user_id, email, section, submission_id) in users:
            if count % PROGRESS_UPDATE_MULTIPLE == 0:
                if progress_bar_update is not None:
                    _ = await progress_bar_update(count, len(users))
                logging.info(f"{count} / {len(users)} Completed")
            count += 1

            submissions = (ed_helper.get_challenge_submissions(
                                user_id, challenge_id
                           ) if not attempt_slide else
                           ed_helper.get_attempt_submissions(
                                user_id, lesson_id, slide_id,
                                submission_id, rubric
                           ))
            # Get all text from final submission box
            if submissions is None:
                continue
            final_submission = submissions[0]
            if final_submission is None:
                continue
            feedback_list.append(submissions[0]['feedback']['content'])
        
        print(feedback_list)
        return feedback_list
    
    @staticmethod
    async def _get_deduction_lines(
        feedback_list: List[str]
    ) -> List[str]:
        # For creative: take everything between "General Deductions:", "Creative Extension:"
        # "Testing/Reflection:"
        deduction_lines = []
        for feedback in feedback_list:
            trim_gen_deductions = re.sub(DeductionsRegex.GENERAL_DEDUCTIONS_PATTERN, '',
                                         feedback)
            trim_creative_ext = re.sub(DeductionsRegex.CREATIVE_EXTENSION_PATTERN, '',
                                       trim_gen_deductions)
            trim_reflection = re.sub(DeductionsRegex.TESTING_REFLECTION_PATTERN, '',
                                     trim_creative_ext)
            deduction_lines.append(trim_reflection)
        
        print(deduction_lines)
        return deduction_lines
    

def extract_comments(
    json_list: List[str]
) -> List[str]:
    """
    Extracts comments from json return 

    Args:
        json_list (List[str]): List of strings from json get call.

    Returns:
        List[str]: List of extracted paragraph texts.
    """
    comments = []
    paragraph_pattern = re.compile(r"<paragraph>(.*?)</paragraph>")

    for json in json_list:
        match = paragraph_pattern.search(json)
        if match:
            comments.append(match.group(1))

    return comments