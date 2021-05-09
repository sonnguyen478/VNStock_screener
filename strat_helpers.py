import os
import logging
import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from strat_configs import fconf

FROM_EMAIL = "sonnguyen478@gmail.com"
PASS_EMAIL = os.environ.get('PASS_EMAIL')
TO_EMAIL = "sonnguyen478@gmail.com"

SLACK_API = ""


def post_message_to_slack(text, blocks = None):
    fconf['slack_token'] = os.environ.get('slack_token', '')
    return requests.post('https://slack.com/api/chat.postMessage', {
        'token': fconf['slack_token'],
        'channel': fconf['slack_channel'],
        'text': text,
#         'icon_url': slack_icon_url,
#         'username': 'monitoring-bot',
        'blocks': json.dumps(blocks) if blocks else None
    }).json()


def post_file_to_slack(slack_channel,
  message, chart_title, file, file_type=None
):
    fconf['slack_token'] = os.environ.get('slack_token', '')
    return requests.post(
      'https://slack.com/api/files.upload', 
      {
        'token': fconf['slack_token'],
        'channels': slack_channel,
        'filename': 'tmp.jpg',
        'filetype': file_type,
        'initial_comment': message,
        'title': chart_title,
      },files={'file': file}).json()


def send_image_to_slack(fig, channel, chart_title, msg="", dpi=100):
    fig.savefig('tmp.jpg', dpi)
    with open('tmp.jpg', 'rb') as img:
        post_file_to_slack(channel, msg, chart_title, file=img, file_type='jpg')


# LOGGER INFO
dir_path = os.path.dirname(os.path.realpath(__file__))
filename = os.path.join(dir_path, 'stock_screener_log.log')

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(filename)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def do_logging(message):
    logger.info(message)


def send_stock_update_email(exportList):
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = "Alert mail (test)"
    #
    message = 'Your favorite stocks pass the condition\n'
    msg.attach(MIMEText(message,'plain'))
    html = """\
    <html>
      <head></head>
      <body>
        {0}
      </body>
    </html>
    """.format(exportList.query('Stock  in {}'.format(fconf['fav_lst'])).to_html())
    part1 = MIMEText(html, 'html')
    msg.attach(part1)
    #
    message = 'ALL stocks pass the condition\n'
    msg.attach(MIMEText(message,'plain'))
    html = """\
    <html>
      <head></head>
      <body>
        {0}
      </body>
    </html>
    """.format(exportList.to_html())
    part2 = MIMEText(html, 'html')
    msg.attach(part2)

    #
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(FROM_EMAIL, PASS_EMAIL)
        smtp.sendmail(msg['From'], msg["To"] , msg.as_string())

        print('DONE')