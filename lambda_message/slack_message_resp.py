import os
import logging
import json
import re
from datetime import datetime, timedelta
from dateutil.parser import parse, ParserError
import requests
from slack import WebClient


##Get enviornment variables
slack_signing_secret = os.environ['SLACK_SIGNING_SECRET']
slack_bot_token = os.environ['SLACK_BOT_TOKEN']
bot_user_id = os.environ['SLACK_BOT_USER_ID']

# Initialize a Web API client
slack_web_client = WebClient(token=slack_bot_token)

##Constants
#time zone name for dc/east coast people
dc_tz = 'Eastern Daylight Time'
dc_tz1 = 'Eastern Standard Time'

ATTACHMENT_COLOR = "#61677A"

QUESTION_BLOCK = {
			"type": "section",
            "block_id": "question",
			"text": {
				"type": "mrkdwn",
				"text": "Do you want to send a timezone message?"
			}
		}
INTRO_BLOCK = {
			"type": "section",
            "block_id": "intro",
			"text": {
				"type": "mrkdwn",
				"text": "Ha! I never forget timezones..."
			}
		}
DIVIDER_BLOCK = {
			"type": "divider"
		}
BUTTON_BLOCK = {
			"type": "actions",
			"block_id": "send_button",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "Yes",
                        "emoji": True
					},
					"value": "send_message",
                    "action_id": "send_button",
                    "style":"primary"
				},
                {
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "No",
                        "emoji": True
					},
					"value": "delete_message",
                    "action_id": "delete_button",
                    "style":"danger"
				}
			]
		}




def getUserTZ(user_id):
    """
    Retrieve time zone information of user with id = user_id

    Parameters:
    user_id (str): the unique id of user

    Returns:
    (str, int, str): the time zone, the UTC offset, and the display name

    """
    response_json = slack_web_client.users_info(user=user_id)

    #get the time zone
    tz_label = response_json["user"]["tz_label"]
    #get the UTC offset
    tz_offset = response_json["user"]["tz_offset"]
    #get the display name
    disp_name = response_json["user"]["profile"]["display_name"]

    return tz_label, tz_offset, disp_name


def getChannelUsersTZ(channel):
    """
    Retrieve time zone information for each user in given channel/group

    Parameters:
    channel (str): the unique id of the channel/group

    Returns:
    dict(str : int), dict(str : str): dictionary with timezones as keys and UTC offsets as values
                                      and a dictionary with timezones as keys and list of display
                                      names in that time zone as values

    """
    response_json = slack_web_client.conversations_members(channel = channel)

    #get a list of members
    members = response_json["members"]

    #initialize dict
    tz_offset_dict = {}
    tz_name_dict = {}

    #iterate through members
    for user_id in members:
        if user_id != bot_user_id:
            tz, tz_offset, disp_name = getUserTZ(user_id)

            #add offset to dict
            if tz not in tz_offset_dict:
                tz_offset_dict[tz] = tz_offset

            #add display names to dict
            if tz not in tz_name_dict:
                tz_name_dict[tz] = [disp_name]
            else:
                tz_name_dict[tz] = tz_name_dict[tz]+[disp_name]

    return tz_offset_dict, tz_name_dict
        

def stringifyDateTime(dt, today):
    """
    Convert given datetime object to string with approproiate formatting

    Parameters:
    dt (datetime): a datetime object

    Returns:
    (str): the datetime formatted as a string

    """
    tomorrow = today + timedelta(days=1)
    yesterday = today - timedelta(days=1)
    d_str = 'on ' + dt.strftime('%a %b-%-d')
    pd_str = 'on ' + dt.strftime('%a %b-%-d')
    t_str = dt.strftime('*%-I:%M%p*')

    #replace with relative date if applicable
    if today.date()==dt.date():
        d_str = 'today'
    elif tomorrow.date()==dt.date():
        d_str = 'tomorrow'
    elif yesterday.date()==dt.date():
        d_str = 'yesterday'

    
    #make AM lowercase to better differentiate
    if t_str[-3:]=="AM*":
        t_str = t_str[:-3]  + 'am' + '*'
    
    #include military time if different than 12 hr
    if dt.strftime('%H').lstrip('0')!=dt.strftime('%-I'):
        t_str = t_str + ' (' + dt.strftime('%H:%M') + ')'

    #if AM add emoji
    if dt.strftime('%p')=="AM":
        t_str = t_str + ' :sunrise:'
    

    return (t_str + ' ' + d_str)


def getTZNames(tz_name_dict, tz):
    """
     Get a string of display names for given tz

    Parameters:
    tz_name_dict (dict{str : str}): dictionary with timezones as keys and display names as values
    tz (str): the time zone

    Returns:
    (str): string listing names in time zone

    """
    #dont create string for eastern time zones
    if tz == dc_tz or tz == dc_tz1:
        return ""

    names = "for *"
    #iterate through list of names
    for name in tz_name_dict[tz]:
        names = names + name + ", "
    names = names.rstrip(", ")
    return names + '*'

def constructBlock(tz, dt, names_str):
    return {
        "type": "section",
#        "block_id": tz,
        "text" : {
            "type": "mrkdwn",
            "text": (dt + "  " + '\n' + names_str)
        }

    }
    

def getTZReply(tz_dict, tz_name_dict, message_dt, sender_offset):
    """
    Construct the slackbot reply

    Parameters:
    tz_dict (dict{str : int}): dictiunary with timezones as keys and UTC offsets as values
    tz_name_dict (dict{str : str}): dictionary with timezones as keys and display names as values
    message_dt (datetime): a datetime object corresponding to the time from the message
    sender_offset (int): the UTC offset of the sender in seconds

    Returns:
    (str): the message the slackbot will send

    """
    #reply = "Ha! I never forget timezones... \n```"
    blocks = [QUESTION_BLOCK, DIVIDER_BLOCK, INTRO_BLOCK]
    #blocks = [INTRO_BLOCK]
    
    #for each timezone and offset
    for tz, offset in tz_dict.items():
        #get the time difference
        delta = offset - sender_offset
        #adjust message time for difference
        dt = message_dt + timedelta(seconds=delta)
        today = datetime.utcnow() + timedelta(seconds=offset)
        #construct response
        #reply = reply + tz + ":  " + stringifyDateTime(dt) + "  " + getTZNames(tz_name_dict, tz) + "\n"
        block = constructBlock(tz, stringifyDateTime(dt,today), getTZNames(tz_name_dict, tz))
        #blocks = blocks + block
        blocks.append(block)

    blocks.append(DIVIDER_BLOCK)
    blocks.append(BUTTON_BLOCK)

    return blocks


def goTZBot(user_id, channel, message):
    """
    Parse message and construct bot reply

    Parameters:
    user_id (str): the unique id of sender
    channel (str): the unique id of the channel/group
    message (str): contents of message from user_id

    Returns:
    (str): the message the slackbot will send
    """
    #search for a time
    result = re.search(
        pattern = 
        '(([0-9]|[0-1][0-9]|[2][0-3]):([0-5][0-9]))|(((^[0-9]|\s[0-9]|@[0-9])|[1][0-9]|[2][0-3])(\s{0,1})(AM|PM|am|pm|aM|Am|pM|Pm{2,2}))',
        string = message)

    #if message includes time
    if result:
        #get the senders UTC offset
        _, sender_offset, _ = getUserTZ(user_id)
        #get the datetime
        default = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(seconds=sender_offset)
        message_dt = parse(message, fuzzy=True, default=default)
        #get timezones and names for channel
        tz_dict, tz_name_dict = getChannelUsersTZ(channel)

        return getTZReply(tz_dict, tz_name_dict, message_dt, sender_offset)

    else:
        #if dateutil has problems parsing - catch it
        raise ParserError()



def handle_message(message_ts, channel_id):
    """
    Get text and user from message timestamp

    Parameters:
    message_ts (str): the unique message timestamp
    channel_id (str): the unique id of the channel/group

    Returns:
    (str,str): the text of the message and the user_id of sender
    """
    message_response = slack_web_client.conversations_history(channel=channel_id,latest=message_ts,limit=1, inclusive=True)
    text = message_response["messages"][0]["text"]
    user_id = message_response["messages"][0]["user"]
    return text, user_id




###### THE LAMBDA FUNCTION #############
# ============== Message Events ============= #
# When a user sends a message in a channel, group, or DM that the bot is in
# the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
def lambda_handler(event, context):
    """
    Parse the message for a time and reply with a timezone message if necessary.

    Parameters:
    payload (json): response from events api
    
    """
    body = json.loads(event['body'])
    event = body['event']
    channel_id = event['channel']
    user_id = event['user']
    text = event['text']

    #if the sender was not the bot
    if(user_id!=bot_user_id): ##hard coded rn - find way to get user_id of bot
        try:
            #construct reply and send
            bot_message = goTZBot(user_id, channel_id, text) # these are my blocks
            response = slack_web_client.chat_postEphemeral(channel=channel_id, user=user_id, blocks = bot_message)
            return{
    	        'statusCode': 200,
    	        'body': ""
                }
        #if dateutil could not find a time   
        except ParserError as p:
            #print("ERROR P")
            return{
    	        'statusCode': 200,
    	        'body': ""
                }
            pass
        
        #to catch other occasional errors
        except TypeError as t:
            #print(t)
            return{
    	        'statusCode': 200,
    	        'body': ""
                }
            pass
    return{
    	    'statusCode': 200,
    	    'body': ""
        }


## for setting up request_url    
def slack_url_setup(event):
    body = event['body']
    body = json.loads(body)
    return{
    	'statusCode': 200,
    	'body': body['challenge']
    }