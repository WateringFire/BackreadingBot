# BackreadingBot
This script library allows CSE 12x/14x TAs to perform various grading assistance checks on Ed assignments and efficiently answer grading questions on Ed. Additionally contains scripts that may be useful throughout the quarter such as consistency checks, mid-quarter csv generation, and minimum grade guarantees.

Note the discord bot is not needed for running any of the local commands (#3-5).

## Table of Contents
1. [Setup](#setup)
2. [Using the Bot](#using-the-bot)
3. [Consistency Checks](#resubmission-consistency-checks)
4. [Mid-Quarter Script](#midquarter-script-generation)
5. [Minimum Grade Calculator](#minimum-grade-guarantee)
6. [Deductions Checker](#deductions-checker)
7. [Development](#development)

## Setup
There is a non-trivial amount of setup required to start executing this discord bot on your local machine, which has been segmented into the 3 primary parts below.
### Python
This bot only works on an older version of python, `python3.9` and the easiest way to get this version is to create a conda environment with this version.
Start by creating a conda environment for the python installation requirements
```bash
conda create -n backreading-bot python=3.9
conda activate backreading-bot
```
Then install the python dependencies:
```bash
pip install -r requirements.txt
pip install discord.py
```
Currently, each of the listed requirements individually may/may not be actually necessary for the bot to function. These are just what was installed on the device used to run the bot in 2022-2024.

### Bash
Give the bash executables permissions to run
```bash
chmod +x bash/keep-running.sh
chmod +x bash/kill.sh
```

### Discord & API Tokens
First, you'll have to actually create and register the Discord application / bot via this [portal](https://discord.com/developers/applications). Create a new application, then create a new Bot within that application (feel free to name both of these what you wish, but the bot's name and image are what will show up on it's discord profile).

When you create the bot, copy it's token and paste it into `store/auth.json`, replacing the string labeled `TODO`. You'll also need to enable the server members and message content intents such that it is able to view server users and read command messages.

To actually add the bot to your discord use the following URL:

https://discord.com/api/oauth2/authorize?client_id=TODO&permissions=1497064598640&scope=bot%20applications.commands

Make sure to replace the client_id TODO with the one found on your Application's OAuth2 page.

## Running the Bot
Note that both of the following scripts assume that you have no other processes running on your computer launched using `python3.9`. Before running, it's worth checking if this assumption is valid via the following command:
```bash
ps -A | grep python3.9
```
If the command returns non-empty results, the following scripts should not be used and you should develop your own version of them that is compatible with the device in question.

To start running the bot execute the following terminal command:
```bash
./bash/keep-running.sh &
```
This will create a wrapper infinitely-looping process that consistently checks whether or not the bot has crashed (this frequently happens to me due to socket-related / internet connectivity issues). If it has, it relaunches so the bot is always up.

If you want to stop these infinitely looping processes (the `keep-running` script and the actual running bot), execute the follwoing:
```bash
./bash/kill.sh
```
This will stop the bot and related wrapper process.

# Using the Bot

If you aren't the owner of the bot in question, or if you've already completed the setup, then the following describes how to use the bot with relevant commands.

## Discord Command Examples
#### Backreading Functionality
The following are all tied to backread request adjacent useful functionality (hence the `br` prefix)
#### br-setup
```!br-setup```
- This command will setup backreading functionality which creates independent threads for assignment questions asked on Ed, allowing leads to organize their conversations surrounding different grading questions. Setting it up will launch a number of setup information queries. The information asked for will be in the following order:
    - Ed API token (via DM)
        - Your token can be found [here](https://edstem.org/us/settings/api-tokens).
    - Link to the staff Ed board to pull from
    - Link of the role to ping when a new thread is made
    - Whether or not you'd like to approve responses before they're made on your account (see `br-push`)
- When completed a #backread-requests thread should be created in the base channel directory (you might have to drag it where you'd like it to be organization-wise).
#### br-stop
```!br-stop```
- This command stops the backreading thread functionality, removing all relevant server information from the bot's database in the process. The previously created #backread-requests channel shouldn't be deleted so it can be referenced against in future quarters.
#### br-push
```!br-push```
- This command should be used in response to a discord message within a #backread-requests thread. Doing so will push the response to Ed on the account linked API token provided on setup.
#### br-pull
```!br-pull```
- This command performs a refresh of #backread-requests threads, pulling in new ones and closing previously answered ones. Note that this is run on a consistent interval by the bot itself, so this is only needed if you'd like to manually pull something into the server and quickly comment on it. 

#### Grading Functionality
The following are all tied to grading adjacent useful functionality (hence the `gr` prefix)
#### gr-check
```gr-check <ASSIGNMENT_LINK>```
- Checks which students that made a submission before the assignment deadline + grace period are missing feedback.
- ASSIGNMENT_LINK
    - Link to the assignment. If using the old Ed "checkpoints", you can just copy and paste the link for the 'Overall Grade' slide here:
i.e: https://edstem.org/us/courses/32019/lessons/51283/slides/296002
    - If using the newer Ed "submissions", you should copy the link for a student's 'Final Submission' slide and remove the student email from the URL:
i.e.: https://edstem.org/us/courses/50191/lessons/87264/attempts?slide=478583
- SCRUBBED_SPREADSHEET
    - Optionally, you can attach a scrubbed spreadsheet .csv file that maps TA name to Ed ID of student graded. If included, the consistency results will map ungraded students to the corresponding TA. If not, it will map to the student's registered section.
#### gr-consistency
```!gr-consistency <ASSIGNMENT_LINK> <CHECK_CONSISTENCY>```
- ASSIGNMENT_LINK
    - Link to the assignment. If using the old Ed "checkpoints", you can just copy and paste the link for the 'Overall Grade' slide here:
i.e: https://edstem.org/us/courses/32019/lessons/51283/slides/296002
    - If using the newer Ed "submissions", you should copy the link for a student's 'Final Submission' slide and remove the student email from the URL:
i.e.: https://edstem.org/us/courses/50191/lessons/87264/attempts?slide=478583
- CHECK_CONSISTENCY
    - Whether or not to check for consistency against the overall feedback template. Expects python boolean value
- SCRUBBED_SPREADSHEET
    - Optionally, you can attach a scrubbed spreadsheet .csv file that maps TA name to Ed ID of student graded. If included, the consistency results will map inconsistencies to the corresponding TA. If not, it will map to the student's registered section.


## (Resubmission) Consistency Checks

Local execution is supported for the checking ungraded and consistency commands for both regular submissions and resubmissions via the `src/commands.py` file. In doing so, as messages are no longer going through discord, you can actually generate *useful* Ed links (as they need to include student emails) if you run things this way. You'll need your [Ed API token](https://edstem.org/us/settings/api-tokens), the link(s) to the assignment(s) you wish to check (specifically, the link to the slide with inputted grades), and some other optional parameters that are explained in more depth via the `--help` flag.

Below is an example of a consistency check for a first-time submission cycle run via this method (with the Ed API token removed):
```bash
python3.9 commands.py -c consistency -e ED_TOKEN -l 'https://edstem.org/us/courses/50191/lessons/87264/attempts?email=jspaniac@uw.edu&slide=478586' -t -s temp/c0.csv
```
The `-c` flag is for which command you'd like to run, `-e` is for your Ed API token, `-l` is for the link to the final submission slide for the assignment, `-t` indicates that we want to check against the overall grading template. The `-s` flag is for the scrubbed spreadsheet mapping TA names to IDs of students they graded; `c0.csv` should be formatted as follows:
```
TA,Student Id
TA_Name,123456
...
```
The `-s` flag is optional, but allows the consistency check to identify which TA is responsible for the consistency issue raised. Additionally, we may supply the `-f` flag to show that we want to have our results be FERPA compliant (not including student emails).

Below is an example of running a resubmission consistency check for a resubmission grading cycle via this method (with the Ed API token removed):
```bash
python commands.py -c consistency_resub -e ED_TOKEN -l 'https://edstem.org/us/courses/67442/lessons/119281/attempts?email=jachi@uw.edu&slide=662732' 'https://edstem.org/us/courses/90026/lessons/155056/attempts?email=iywang@uw.edu&slide=904654' -t -s temp/c0.csv temp/p0.csv -d RESUB_DEADLINE
```
This command is run assuming you have a `temp` directory in the root of the project, and that you have a `c0.csv` and `p0.csv` file in that directory that maps TA names to student Ed IDs that they graded. (It is recommended to supply spreadsheets with the `-s` argument to speed up consistency checks, though it is possible to run without.) The `c0.csv` and `p0.csv` files should have the same format as the scrubbed spreadsheet described above.

Note the differences from a regular consistency check:
- You may check *multiple assignments* in one command run by supplying multiple assignment links (and the spreadsheet corresponding to each) as space-separated values. This allows you to run the command just one time for resubmission consistency checks, rather than running it once per assignment eligible in the current resubmission cycle. The [Abbreviating Local Commands](#abbreviating-local-commands) section describes how you could further simplify the resubmission consistency check command.
- You must specify the due date of the resubmission following the `-d` flag, formatted as `MM/DD/YY HH:MM:SS` (this matches the `strptime` format `%m/%d/%y %H:%M:%S`). By default, the consistency check will use the *America/Los_Angeles* region for the due date's timezone, and has a grace period of 0 minutes.

## Abbreviating Local Commands

Because supplying the assignment link(s) each time you run consistency checks can be tedious, there is an alternative option for both regular and resubmission consistency checks. Rather than providing all assignment links on the command line, you can instead use the `-a` flag to provide a configuration file of all the assignment links for the quarter *along with* the `-n` flag to indicate which of those assignments to check.

The configuration file should be formatted to consist of multiple rows, where each row is the link to the *final submission* slide for an assignment. The `-n` flag accepts one or multiple numbers; each number indicates that the consistency check will be run for the assignment link at that row number (1-indexed) of the configuration file. Similar to when the command accepts multiple assignment links, the number of values following the `-n` flag should be equal to the number of spreadsheets following the `-s` flag.

Below is an example of a consistency check (for a resubmission) run via this method (with the Ed API token removed):
```bash
python3.9 commands.py -c consistency_resub -e ED_TOKEN -a temp/CONFIGURATION_FILE_NAME -n 2 3 -t -s temp/SPREADSHEET_NAME_1 temp/SPREADSHEET_NAME_2 -d RESUB_DEADLINE
```
`-n 2 3` will use the assignment links in the 2nd and 3rd rows (1-indexed) of the configuration file located at `temp/CONFIGURATION_FILE_NAME`.

## Midquarter Script Generation
In addition to consistency checks, you may also need to generate the midquarter check-in form grades. This pulls all grades from the provided assignment links (see below) and their previous grades as well (resubmissions). Optionally if provided, the script can add on whether or not a student attended quiz (currently only quiz 0 allowed).

Provide assignment links before running the command in `temp/assignments.txt`. The links should copied from the final submission slide when viewing feedback on your own submission and look similar to `https://edstem.org/us/courses/97143/lessons/162783/attempts?email=colinlim@uw.edu&slide=957466`.

If quiz attendance is desired, download from Gradescope and place the "`Quiz_0_Version_Set_Scores.csv`" in folder labelled `temp/` as well. Name should exactly match.

After everything is provided, run the following command with your ED Token. The `-n` flag tells it how many assignemnts from the `temp/assignments.txt` file you would like to grab grades from. These should be space separated line numbers matching the assignment link number (1-indexed)
```bash
python3.9 commands.py -c midquarter -e ED_TOKEN -a temp/assignments.txt -n 1 2
```

## Minimum Grade Guarantee

### NOTE: Currently in developemnt, does support pulling grades from quizzes yet.

You may also want to calculate grade guarantees for students. To pull all grades and calculate the minimum grade for students, create a folder `/temp` in the home directory and create a file called `assignments.txt` (to work with mid quarter script as well).

The file should contain links from the "Submission and Grades" on the "Final Submission" slide on yourself for every assignment in the course. Every different assignment link should be on a new line. An example link is as follows:
`https://edstem.org/us/courses/97143/lessons/162783/attempts?email=colinlim@uw.edu&slide=957466`. 

Finally, run the following command and wait for a while and find the resulting csv in the `/temp` directory.
```bash
python3.9 commands.py -c grade_calculator -e ED_TOKEN -a temp/assignments.txt
```

## Deductions Checker
To pull all deductions from all submissions for an assignment, use the followng command:
```bash
python3.9 commands.py -c deductions -e ED_TOKEN -a temp/deductions_assignments.txt -n 1
```
The `-a` is directory of assignment links (url should be grabbed from the coding slide while viewing feedback) separated by newlines.
The `-n` flag should be the number of those links wanting to be pulled
The `-e` flag is required with an ed token.


# Development
## Directory Layout
- `bash`
    - Where the bash scripts are located
    - `keep-running.sh`
        - Allows the bot to relaunch itself on crash
    - `kill.sh`
        - Kills both the currently running bot and `keep-running.sh`
- `src`
    - Where the actual library implementations exist.
    - `consistency_checker.py`
        - Running consistency checks:
            - Making sure selected dropdown matches value in overall feedback box
            - Most recent / final submission before assignment deadline graded
            - TA email left on student submission
            - etc.
    - `consistency_resub_checker.py`
        - Running resub consistency checks:
            - Making sure selected dropdown matches value in overall feedback box
            - Most recent / final submission before resubmission deadline graded
            - TA email left on student submission
            - etc.
    - `constants.py`
        - Constant definition within the bot
            - Might be worth changing for your specific use case
    - `database.py`
        - Wrapper for database mapping
            - Connects server_id to relevant course information
    - `discord_helper.py`
        - Useful discord-related commands:
            - Getting user from server
            - Sending message to channel
            - etc.
    - `ed_helper.py`
        - Makes Ed API calls / restructures API response data in a more usable fashion
    - `exceptions.py`
        - Custom exception definitions used throughout the library
    - `html_constants.py`
        - Used to create HTML consistency_checker table formatting
    - `utils.py`
        - Useful functions used throughout the library
- `store`
    - For general storage purposes. Houses the physical database file and the user's Ed API token.
    - `logging`
        - Where the active logs are stored
- `temp`
    - Used by the bot when creating .csv / .html files for temporary storage before uploading to discord.
- `tests`
    - Where the 
- `bot.py`
    - Launch this to run the python bot
- `commands.py`
    - Local versions of the bot commands
