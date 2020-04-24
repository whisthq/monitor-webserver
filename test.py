import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail

print(os.environ['SENDGRID_API_KEY'])

# title = 'Test'
# message = "test"
# internal_message = SendGridMail(
#     from_email = 'mingying2011@gmail.com',
#     to_emails = ['logs@fractalcomputers.com'],
#     subject = title,
#     html_content= message
# )
# try:
#     sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
#     response = sg.send(internal_message)
# except:
#     file = open("log.txt", "a") 
#     file.write(datetime.utcnow().strftime('%m-%d-%Y, %H:%M:%S') + " ERROR while reporting error: " + traceback.format_exc())
#     file.close()