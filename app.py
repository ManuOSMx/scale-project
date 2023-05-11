import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os
import json
load_dotenv()

API_KEY = os.getenv("LIVE_API_KEY")
API_URL = "https://api.scale.com/v1/tasks?project=Traffic%20Sign%20Detection&status=completed"
PROJECT_NAME = 'Traffic Sign Detection'
headers = {"accept": "application/json"}
auth = HTTPBasicAuth('{}'.format(API_KEY),'')
response = requests.request("GET", API_URL, headers=headers, auth=auth)

# Transform JSON to Dictionary
JSON_load = json.loads(response.text)

# Only to verify information
object_to_annotate_name = 'traffic_control_sign'
object_to_annotate_name_2 = 'non_visible_face'

warnings_list = []
warnings_list_task = []
errors_list = []
errors_list_task = []
total_errors = 0
total_warnings = 0

def add_error(l_id, l_name, e_msg):
    errors_list_task.append({
            'uuid': l_id,
            'label': l_name,
            'error_message': e_msg
        })
    return True

def add_warning(l_id, l_name, w_msg):
    warnings_list_task.append({
            'uuid': l_id,
            'label': l_name,
            'warning_message': w_msg
        })
    return True

def check_occlusion_truncation(label_id, label_name, percentage_occlusion,percentage_truncation):
    warning_message = 'Nothing'
    percentage_oc_num = percentage_occlusion.replace("%","")
    percentage_tr_num = percentage_truncation.replace("%","")
    percentage_oc_num, percentage_truncation = int(percentage_oc_num),int(percentage_tr_num)

    if (percentage_oc_num >= 75):
        warning_message = 'Warning, this box probably has an occlusion of 75 percent or more, verify that it is correct.'
        add_warning(label_id, label_name, warning_message)
        return True
    elif(percentage_truncation >= 75):
        warning_message = 'Warning, this box probably has an truncation of 75 percent or more, verify that it is correct.'
        add_warning(label_id, label_name, warning_message)
        return True
    check_result = True if (percentage_oc_num >= 75 and percentage_truncation >= 75) else False
    if check_result:
        warning_message = 'Warning, this box probably has an truncation of 75 percent or more and occlusion of 75 percent or more, verify that it is correct.'
        add_warning(label_id, label_name, warning_message)
        return True
    
    return False

def check_label_bg_color(label_id,label_name, label_color):
    error_message = 'Nothing'
    if((label_name != 'non_visible_face') and (label_color == 'not_applicable')):
        error_message = "Error: Background color “not_applicable” should be used for the “non_visible_face” label."
        add_error(label_id, label_name, error_message)
        return True
    elif((label_name == 'non_visible_face') and (label_color == 'other')):
        error_message = "Error: Background color “other” should not be used for the “non_visible_face” label."
        add_error(label_id, label_name, error_message)
        return True
    
    return False
    
for task in JSON_load['docs']:
    task_error_flag, task_warning_flag = False, False
    task_annotations = task['response']['annotations']
    print("======== TASK {}".format(task['task_id']))
    for annotation in task_annotations:
        annotation_id = annotation['uuid']
        annotation_label = annotation['label']
        annotation_bg_color = annotation['attributes']['background_color']
        annotation_occlusion = annotation['attributes']['occlusion']
        annotation_truncation = annotation['attributes']['truncation']
        
        check_label_bg_color(annotation_id, annotation_label, annotation_bg_color)
        check_occlusion_truncation(annotation_id, annotation_label, annotation_occlusion, annotation_truncation)
        task_error_flag =  True if errors_list_task else False
        task_warning_flag =  True if warnings_list_task else False

    if (task_error_flag == True):
        errors_list.append({
            'task_id': task['task_id'],
            'errors_information': errors_list_task,
            'task_error_counter': len(errors_list_task)
        })
        total_errors += len(errors_list_task)
        errors_list_task = []
        task_error_flag = False

    elif (task_warning_flag == True):
        warnings_list.append({
            'task_id': task['task_id'],
            'warning_information': warnings_list_task,
            'task_warning_counter': len(warnings_list_task)
        })
        total_warnings += len(warnings_list_task)
        warnings_list_task = []
        task_warning_flag = False

with open('output.json', 'w') as outfile:
    json.dump({'warnings_detected': warnings_list, 'errors_detected': errors_list, 'total_warnings': len(warnings_list),'total_errors': total_errors}, outfile)