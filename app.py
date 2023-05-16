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

def save_box(box_id, box_label, box_x, box_y, box_w, box_h):
    if(annotation_label != object_to_annotate_name_2):
        box_perimeter = (2 * box_w) + (2 * box_h)
        boxes_area.append(
            {
                "box_id": box_id,
                "box_label": box_label,
                "position_left":  box_x,
                "position_top":  box_y,
                "width": box_w,
                "height": box_h,
                "size": box_perimeter
            })
    return True

def calculate_overlap_area(box1, box2):
    # Calculate the position of the upper left corner
    x_overlap = max(0, min(box1['position_left'] + box1['width'], box2['position_left'] + box2['width']) - max(box1['position_left'], box2['position_left']))
    y_overlap = max(0, min(box1['position_top'] + box1['height'], box2['position_top'] + box2['height']) - max(box1['position_top'], box2['position_top']))
    
    overlap_area = x_overlap * y_overlap
    return overlap_area


def check_overlap(boxes_area):
    check_oversize(boxes_area)
    for i in range(len(boxes_area)):
        for j in range(i+1, len(boxes_area)):
            # Box 1 and Box 2 areas
            area1 = boxes_area[i]['width'] * boxes_area[i]['height']
            area2 = boxes_area[j]['width'] * boxes_area[j]['height']
            
            overlap_area = calculate_overlap_area(boxes_area[i], boxes_area[j])

            overlap_percentage1 = overlap_area / area1
            overlap_percentage2 = overlap_area / area2
            
            # Overlap 50% or 75%
            max_percent = 0.5
            if overlap_percentage1 > max_percent or overlap_percentage2 > max_percent:
                warning_message = f"Warning, uuid: {boxes_area[i]['box_id']} , {boxes_area[i]['box_label']} AND uuid: {boxes_area[j]['box_id']} , {boxes_area[i]['box_label']} overlap by more than 75%"
                add_warning(boxes_area[i]['box_id'], boxes_area[i]['box_label'], warning_message)
                return True
    
    return False

def box_perimeter(sqr_w, sqr_h,sqr_id,sqr_label):
    box_width = sqr_w
    box_height = sqr_h
    box_perimeter_result = (2 * box_width) + (2 * box_height)
    box_info = {'box_id' : sqr_id, 'box_label': sqr_label ,'size' : box_perimeter_result}
    box_perimeters_list.append(box_info)

def sum_perimeters(sqr_list):
    total = 0
    for sqr_size in sqr_list:
        total += sqr_size['size']
    return total

def check_oversize(box_list):
    factor = 4
    perimeter_average = sum_perimeters(box_list) / len(box_list)
    max_size = perimeter_average * factor
    for box in box_list:
        if box['size'] > max_size:
            warning_message = (f"The uuid: {(box['box_id'])} has an area that is too large compared to the average of all the areas. Please, verify if this is correct.")
            add_warning(box['box_id'], box['box_label'], warning_message)
            return True
    return False
            
for task in JSON_load['docs']:
    box_perimeters_list = []
    boxes_area = []
    task_error_flag, task_warning_flag = False, False
    task_annotations = task['response']['annotations']
    # print("======== TASK {}".format(task['task_id']))
    for annotation in task_annotations:
        annotation_id = annotation['uuid']
        annotation_label = annotation['label']
        annotation_bg_color = annotation['attributes']['background_color']
        annotation_occlusion = annotation['attributes']['occlusion']
        annotation_truncation = annotation['attributes']['truncation']
        annotation_position_x = annotation['left']
        annotation_position_y = annotation['top']
        annotation_height = annotation['height']
        annotation_width = annotation['width']
        
        check_label_bg_color(annotation_id, annotation_label, annotation_bg_color)
        check_occlusion_truncation(annotation_id, annotation_label, annotation_occlusion, annotation_truncation)
        save_box(annotation_id, annotation_label, annotation_position_x, annotation_position_y, annotation_width, annotation_height)
        box_perimeter(annotation['width'],annotation['height'], annotation['uuid'], annotation['label'])

    check_overlap(boxes_area)
    check_oversize(box_perimeters_list)
    task_error_flag =  True if errors_list_task else False
    task_warning_flag =  True if warnings_list_task  else False

    if (task_error_flag == True):
        errors_list.append({
            'task_id': task['task_id'],
            'errors_information': errors_list_task,
            'task_error_counter': len(errors_list_task)
        })
        total_errors += len(errors_list_task)
        errors_list_task = []
        task_error_flag = False

    if (task_warning_flag == True):
        warnings_list.append({
            'task_id': task['task_id'],
            'warning_information': warnings_list_task,
            'task_warning_counter': len(warnings_list_task)
        })
        total_warnings += len(warnings_list_task)
        warnings_list_task = []
        task_warning_flag = False

with open('output.json', 'w') as outfile:
    json.dump({'warnings_detected': warnings_list, 'errors_detected': errors_list, 'total_warnings': total_warnings,'total_errors': total_errors}, outfile)

print("JSON file ( output.json ) has been successfully created") 