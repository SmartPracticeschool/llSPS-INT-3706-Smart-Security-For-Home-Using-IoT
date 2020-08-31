import time
import json
import cv2
import numpy as np
import datetime
import winsound
import sys
from os.path import join, dirname
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from sys import platform

#ObjectStorage
import ibm_boto3
from ibm_botocore.client import Config, ClientError

#CloudantDB
from cloudant.client import Cloudant
from cloudant.error import CloudantException
from cloudant.result import Result, ResultByKey
import requests

authenticator = IAMAuthenticator('fKtLqaBOWkrrdu6Tb316mbMb7onFhufoZw8mDI_knE8y')
speech_to_text = SpeechToTextV1(
        authenticator=authenticator
        )
speech_to_text.set_service_url('https://api.eu-gb.speech-to-text.watson.cloud.ibm.com/instances/a5b62714-d9f5-4451-a9b6-9470d4dea33c')
        
# Constants for IBM COS values
COS_ENDPOINT = "https://s3.jp-tok.cloud-object-storage.appdomain.cloud" # Current list avaiable at https://control.cloud-object-storage.cloud.ibm.com/v2/endpoints
COS_API_KEY_ID = "dP3PJ07OoV2jV5HwkdBl36IkVqoA4tgQKNUdpTXMIgIJ" # eg "W00YiRnLW4a3fTjMB-odB-2ySfTrFBIQQWanc--P3byk"
COS_AUTH_ENDPOINT = "https://iam.cloud.ibm.com/identity/token"
COS_RESOURCE_CRN = "crn:v1:bluemix:public:cloud-object-storage:global:a/e389dfaec4bf49fd8616a7c79173bf2a:c9a7f7c5-abba-4f2a-b05f-49491c2454e3::" # eg "crn:v1:bluemix:public:cloud-object-storage:global:a/3bf0d9003abfb5d29761c3e97696b71c:d6f04d83-6c4f-4a62-a165-696756d63903::"



def askUser():
    def door_open(): 
        #reading voice command
        with open(join(dirname(__file__), './.', 'open.mp3'),
                    'rb') as audio_file:
                speech_recognition_results = speech_to_text.recognize(
                audio=audio_file,
                content_type='audio/mp3'
            ).get_result()
        x = speech_recognition_results["results"][0]["alternatives"][0]["transcript"]
        print('The received voie command is: %s\n' %x)
        print("opening...\n")
        time.sleep(1)
        print("The door has been opened. Please enter.\n")
        
    def door_close():
        #reading voice command
        with open(join(dirname(__file__), './.', 'close.mp3'),
                    'rb') as audio_file:
                speech_recognition_results = speech_to_text.recognize(
                audio=audio_file,
                content_type='audio/mp3'
            ).get_result()
        x = speech_recognition_results["results"][0]["alternatives"][0]["transcript"]
        print('The received voice command is: %s\n' %x)
        print("closing...\n")
        time.sleep(1)
        print("The door has been closed.\n")
        
    def help():
        #reading voice command
        with open(join(dirname(__file__), './.', 'help.mp3'),
                    'rb') as audio_file:
                speech_recognition_results = speech_to_text.recognize(
                audio=audio_file,
                content_type='audio/mp3'
            ).get_result()
        x = speech_recognition_results["results"][0]["alternatives"][0]["transcript"]
        print('The received voice command is: %s\n' %x)
        # Create resource
        cos = ibm_boto3.resource("s3",
            ibm_api_key_id=COS_API_KEY_ID,
            ibm_service_instance_id=COS_RESOURCE_CRN,
            ibm_auth_endpoint=COS_AUTH_ENDPOINT,
            config=Config(signature_version="oauth"),
            endpoint_url=COS_ENDPOINT
        )
        print("Connection to object storage is successful.\n")

        #Provide CloudantDB credentials such as username,password and url
        client = Cloudant("9c5c6638-7905-4a84-83a4-1cb261eda0fb-bluemix", "c03337ec5509d46ac72da329e4d06d887a52c4e4c6b2966d3b2fcf4c06c5a863", url="https://9c5c6638-7905-4a84-83a4-1cb261eda0fb-bluemix:c03337ec5509d46ac72da329e4d06d887a52c4e4c6b2966d3b2fcf4c06c5a863@9c5c6638-7905-4a84-83a4-1cb261eda0fb-bluemix.cloudantnosqldb.appdomain.cloud")
        client.connect()

        #Provide your database name
        database_name = "sample"
        my_database = client.create_database(database_name)

        if my_database.exists():
           print("Database creation is successful.\n")


        def multi_part_upload(bucket_name, item_name, file_path):
            try:
                print("Starting file transfer for {0} to cloud bucket: {1}\n".format(item_name, bucket_name))
                # set 5 MB chunks
                part_size = 1024 * 1024 * 5

                # set threadhold to 15 MB
                file_threshold = 1024 * 1024 * 15

                # set the transfer threshold and chunk size
                transfer_config = ibm_boto3.s3.transfer.TransferConfig(
                    multipart_threshold=file_threshold,
                    multipart_chunksize=part_size
                )

                # the upload_fileobj method will automatically execute a multi-part upload
                # in 5 MB chunks for all files over 15 MB
                with open(file_path, "rb") as file_data:
                    cos.Object(bucket_name, item_name).upload_fileobj(
                        Fileobj=file_data,
                        Config=transfer_config
                    )
                
                print("Transfer of the image file {0} is complete!\n".format(item_name))
            except ClientError as be:
                print("CLIENT ERROR: {0}\n".format(be))
            except Exception as e:
                print("Unable to complete multi-part upload: {0}\n".format(e))
                
                
        #Reading the first frame/image of the video.
        video=cv2.VideoCapture(0)

        #capturing the first frame
        check,frame=video.read()
        gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        picname=datetime.datetime.now().strftime("%y-%m-%d-%H-%M-%S")
        cv2.imwrite(picname+".jpg",frame)
        print("Image captured and saved in local storage\n")
        multi_part_upload("bishwa-bucket-2020", picname+".jpg", picname+".jpg")
        json_document={"link":COS_ENDPOINT+"/"+"bishwa-bucket-2020"+"/"+picname+".jpg"}
        new_document = my_database.create_document(json_document)

        # Checking that the document exists in the database.
        if new_document.exists():
           print("Document creation is successful.\n")
           
        #Sending alert message to mobile   
        r = requests.get('https://www.fast2sms.com/dev/bulk?authorization=k09lbxTwofiG5zstSpW18MIjZB3CFrNmEUOe7cRPQa4dnhH2KDkRubGmzV0jQTOr6gAEvqCWh3I87512&sender_id=FSTSMS&message=Alert! Tresspassers Detected&language=english&route=p&numbers=7855098552')
        #print(r.status_code)
        print("Sending alert message to mobile is successful.\n")
        
        #Sending Buzzer Alert
        print("Buzzer alert sent.\n")
        if platform == "linux" or platform == "linux2" or platform == "darwin":
           duration = 1  # Set duration to 1 second
           freq = 2500  # Set frequency To 2500 He
           os.system('play -nq -t alsa synth {} sine {}'.format(duration, freq))
        elif platform == "win32":
           frequency = 2500  # Set frequency To 2500 Hertz
           duration = 1000  # Set duration To 1000 ms == 1 second
           winsound.Beep(frequency, duration)

        #release the camera
        video.release()
        print("camera released")
        
    def shut():
        print("shutting down...")
        sys.exit(0)
        
    choice_dict = {1:door_open, 2:door_close, 3:help, 4:shut}

    while True:
        try:
            choices = list(map(int,input("\nHello! I am your smart home assistant. Input your voice command:\n \n(1) for opening the door. \n(2) for closing the door. \n(3) for help. \n(4) for shutting down smart home assistant.\n").split()))
        except ValueError:
            print("Input your command\n")
            continue
        for choice in choices:
            if 0 < choice and choice < 5:
                choice_dict[choice]()
            else:
                print("Please input a valid choice between 1 and 4!")
askUser()