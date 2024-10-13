import cv2
import numpy as np
import pyautogui
import pytesseract
import keyboard
import sys
import time
from enum import Enum
import os
import asyncio


WAITING_SCREEN = [[184, 232, 251], [255, 194, 160]]
MATCH_SUCCESS = [[216, 255,  95], [255, 255, 255]]
PRE_MATCH = [[255, 255, 239], [255, 255, 255]]
REWARD_SCREEN = [[125, 110,  70], [76, 66, 50]]
CONTINUE_PK = [[ 46, 133, 208], [ 10, 122, 212]]

class GameState(Enum):
    BOOTING = 0
    MM_ING = 1
    MM_COMPLETE = 2
    PRE_MATCH = 3
    IN_MATCH = 4
    END_MATCH = 5
    GET_REWARD = 6
    REMATCH = 7
    UNKNOWN = 8

pytesseract.pytesseract.tesseract_cmd = r'D:\Program Files\Tesseract-OCR\tesseract.exe'

def getPixColor(img, x, y):
    return img[y, x]

def comparePixColorDiff(color_1, color_2):
    diff = 0
    for i in range(3):
        diff += abs(int(color_1[i]) - int(color_2[i]))
    return diff

def capture_area(region):
    screenshot = pyautogui.screenshot(region=region)
    return np.array(screenshot)

def state_control(current_state, playground):

    pic = capture_area(playground)
    middle = [int(pic.shape[1] / 2), int(pic.shape[0] / 2)]
    middle_up = [middle[0]-100, middle[1] - 20]
    middle_down = [middle[0]+100, middle[1] + 20]
    #draw a rectangle to show the area of the middle_up and middle_down
    # cv2.rectangle(pic, (middle_up[0], middle_up[1]), (middle_down[0], middle_down[1]), (0, 255, 0), 3)
    # cv2.imshow("pic", pic)
    # cv2.waitKey(0)
    # exit(0)
    middle_up = [middle[0], middle[1] - 20]
    middle_down = [middle[0], middle[1] + 20]
    up_color = getPixColor(pic, middle_up[0], middle_up[1])
    down_color = getPixColor(pic, middle_down[0], middle_down[1])
    #print the color of two points as 2d array
    # print("[{}, {}]".format(up_color, down_color))
    # cv2.circle(pic, (middle_up[0], middle_up[1]), 5, (0, 0, 255), -1)
    # cv2.circle(pic, (middle_down[0], middle_down[1]), 5, (0, 0, 255), -1)
    #continue to show the pic with two points
    # cv2.imshow("pic", pic)
    # cv2.waitKey(0)
    diff = [0, 0, 0, 0, 0]
    diff[0] = comparePixColorDiff(up_color, WAITING_SCREEN[0]) + comparePixColorDiff(down_color, WAITING_SCREEN[1])
    diff[1] = comparePixColorDiff(up_color, MATCH_SUCCESS[0]) + comparePixColorDiff(down_color, MATCH_SUCCESS[1])
    diff[2] = comparePixColorDiff(up_color, PRE_MATCH[0]) + comparePixColorDiff(down_color, PRE_MATCH[1])
    diff[3] = comparePixColorDiff(up_color, REWARD_SCREEN[0]) + comparePixColorDiff(down_color, REWARD_SCREEN[1])
    diff[4] = comparePixColorDiff(up_color, CONTINUE_PK[0]) + comparePixColorDiff(down_color, CONTINUE_PK[1])

    min_diff = min(diff)
    if min_diff >= 250 and current_state != GameState.IN_MATCH:
        print("自动机未找到匹配状态|{}|,diff array:{}".format(GameState.UNKNOWN,diff))
        return GameState.UNKNOWN
    min_index = diff.index(min_diff)

    if current_state == GameState.BOOTING:
        if min_index == 0:
            print("当前状态：匹配中")
            return GameState.MM_ING
        else:
            return GameState.UNKNOWN
    elif current_state == GameState.MM_ING:
        if min_index == 1:
            print("当前状态：匹配完成")
            return GameState.MM_COMPLETE
        else:
            return GameState.UNKNOWN
    elif current_state == GameState.MM_COMPLETE:
        if min_index == 2:
            print("当前状态：准备开始")
            return GameState.PRE_MATCH
        else:
            return GameState.UNKNOWN
    elif current_state == GameState.PRE_MATCH:
        #wait
        return GameState.IN_MATCH
    elif current_state == GameState.END_MATCH:
        if min_index == 3:
            print("当前状态：游戏结束,领取奖励")
            return GameState.GET_REWARD
        else:
            return GameState.UNKNOWN
    elif current_state == GameState.GET_REWARD:
        if min_index == 4:
            print("当前状态：继续PK")
            return GameState.REMATCH
        else:
            return GameState.UNKNOWN
    elif current_state == GameState.REMATCH:
        if min_index == 0:
            print("当前状态：匹配中")
            return GameState.MM_ING
        else:
            return GameState.UNKNOWN

def recognize_numbers(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #get blue channel
    blue = image[:, :, 0]
    #find the position of two point where color changed to 255 and back to others
    first = 0
    second = 0
    for i in range(0, blue.shape[1]-1):
        if blue[5][i] >= 240:
            first = i
            break
    for i in range(first, blue.shape[1]-1):
        if blue[5][i] < 240:
            second = i
            break
    #draw two lines to show the position of the two points
    # cv2.line(image, (first, 0), (first, image.shape[0]), (0, 255, 0), 3)
    # cv2.line(image, (second, 0), (second, image.shape[0]), (0, 255, 0), 3)
    # cv2.imshow("image", image)
    # cv2.waitKey(0)
    #cut the image into 3 halfs by the two points
    gray_left = gray[:, 0:first]
    gray_right = gray[:, second:]

    _, thresh_left = cv2.threshold(gray_left, 150, 255, cv2.THRESH_BINARY)
    _, thresh_right = cv2.threshold(gray_right, 150, 255, cv2.THRESH_BINARY)
    try:
        text_left = pytesseract.image_to_string(thresh_left, config='--psm 6')
        text_right =  pytesseract.image_to_string(thresh_right, config='--psm 6')
    except:
        return None

    text_left = text_left.replace(" ", "").replace("i)", "9")
    text_right = text_right.replace(" ", "").replace("i)", "9")
    # if text left and text right are not string numbers, return None
    try:
        int(text_left)
        int(text_right)
    except ValueError:
        return None
    numbers = [int(text_left), int(text_right)]
    return numbers

def click(pos):
    pyautogui.mouseDown(pos[0], pos[1], button='left')
    time.sleep(0.1)
    pyautogui.mouseUp(pos[0], pos[1], button='left')
    pyautogui.click(pos[0], pos[1], button='left')

def draw_less_than(pos):
    pyautogui.moveTo(pos[0], pos[1], duration=0.002)
    pyautogui.mouseDown(pos[0], pos[1], button='right', duration=0.002)
    # pyautogui.moveTo(pos[0] - 100, pos[1]+50, duration=0.002)
    # pyautogui.mouseUp(pos[0], pos[1] + 100, button='left', duration=0.002)
    # pyautogui.moveTo(pos[0], pos[1], duration=0.002)
    pyautogui.mouseUp(pos[0], pos[1], button='right', duration=0.002)

def draw_greater_than(pos):
    pyautogui.moveTo(pos[0], pos[1], duration=0.002)
    pyautogui.mouseDown(pos[0], pos[1], button='middle', duration=0.002)
    # pyautogui.moveTo(pos[0] + 100, pos[1]+50, duration=0.002)
    # pyautogui.mouseUp(pos[0], pos[1] + 100, button='left', duration=0.002)
    # pyautogui.moveTo(pos[0], pos[1], duration=0.002)
    pyautogui.mouseUp(pos[0], pos[1], button='middle', duration=0.002)

def locate_playground():
    window = pyautogui.getWindowsWithTitle("Wormhole")[0]
    if window is None:
        print("未找到窗口")
        exit(1)
    windows_rect = [window.left, window.top, window.right - window.left, window.bottom - window.top]
    sc = pyautogui.screenshot(region=(windows_rect[0], windows_rect[1], windows_rect[2], windows_rect[3]))
    if os.path.exists("playground_location.txt"):
        with open("playground_location.txt", "r") as file:
            lines = file.readlines()
            phone = eval(lines[0].split(": ")[1])
            progress = eval(lines[1].split(": ")[1])
            question = eval(lines[2].split(": ")[1])

        result = [progress, question, windows_rect, phone]
        result[0] = [int(i) for i in result[0]]
        result[1] = [int(i) for i in result[1]]
        result[2] = [int(i) for i in result[2]]
        result[3] = [int(i) for i in result[3]]
        return result
        
        
    else:
        print("playground_location.txt 文件不存在，正在创建...")
        #找到手机界面的位置
        sc = np.array(sc)
        sc_hsv = cv2.cvtColor(sc, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 200, 200])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(sc_hsv, lower_green, upper_green)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        max_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(max_contour)
        phone = [x, y, w, h]
        # cv2.rectangle(sc, (x, y), (x + w, y + h), (0, 255, 0), 3)
        #找到口算题的位置
        sc_phone = sc[y:y+h, x:x+w]
        question = [0,0,0,0]
        question[0] = phone[0] + int(w / 8)
        question[1] = phone[1] + int(h / 10 * 2.5)
        question[2] = int(w / 8 * 6)
        question[3] = int(h / 10 * 1)

        cv2.rectangle(sc, (question[0], question[1]), (question[0] + question[2], question[1]
                    + question[3]), (0, 255, 0), 3)
        #找到进度条的位置
        progress = [0,0,0,0]
        progress[0] = phone[0] + int(w / 7 * 3)
        progress[1] = phone[1] + int(h / 19)
        progress[2] = int(w / 7)
        progress[3] = int(h / 19)
        cv2.rectangle(sc, (progress[0], progress[1]), (progress[0] + progress[2], progress[1]
                    + progress[3]), (0, 255, 0), 3)
        # cv2.imshow("sc", sc)
        # cv2.waitKey(0)
        #create a new file to save the location of the phone, progress and question
        with open("playground_location.txt", "w") as file:
            file.write(f"Phone: {phone}\n")
            file.write(f"Progress: {progress}\n")
            file.write(f"Question: {question}\n")

        return [progress, question, windows_rect, phone]
    
def recognize_progress(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresh, config='--psm 6')
    if text.find("/") == -1:
        return [0,0]
    hash_pos = text.find("/")
    current_pos = int(text[0:hash_pos])
    total_pos = int(text[hash_pos+1])
    total_pos *= 10
    if current_pos < 0 or current_pos > 100:
        print("未找到正确的进度")
        return [0,0]
    return [current_pos, total_pos]

def compare_numbers(numbers):
    if len(numbers) < 2:
        print("比大小失败")
        return None
    first, second = numbers[0], numbers[1]
    if first > second:
        return True
    else:
        return False

def main():
    playground = locate_playground()
    progress = playground[0]
    question = playground[1]
    windows_rect = playground[2]
    phone = playground[3]
    #增加偏移量
    progress[0] += windows_rect[0]
    progress[1] += windows_rect[1]
    question[0] += windows_rect[0]
    question[1] += windows_rect[1]
    phone[0] += windows_rect[0]
    phone[1] += windows_rect[1]
    draw_pos = [phone[0] + int(phone[2] / 2), phone[1] + int(phone[3] / 2) + 50]
    reward_btn_pos = [phone[0] + int(phone[2] / 2), phone[1] + int(phone[3] / 2) + 180]
    continuePK_btn_pos = [phone[0] + int(phone[2] / 2) + 120, phone[1] + int(phone[3] / 2) + 380]
    continue_btn_pos = [phone[0] + int(phone[2] / 2) + 120, phone[1] + int(phone[3] / 2) + 480]
    next_que = [question[0], question[1]+130, question[2], int(question[3]/2)]
    state = GameState.BOOTING
    while True:
        temp_state = state_control(state, phone)
        while temp_state == GameState.UNKNOWN:
            temp_state = state_control(state, phone)
            time.sleep(0.1)
        state = temp_state

        #根据状态执行不同的操作
        if (state == GameState.BOOTING or state == GameState.MM_ING 
        or state == GameState.MM_COMPLETE or state == GameState.PRE_MATCH
        or state == GameState.END_MATCH):
            continue
        elif state == GameState.GET_REWARD:
            time.sleep(1.5)
            click(reward_btn_pos)
            time.sleep(0.5)
            click(continue_btn_pos)
        elif state == GameState.REMATCH:
            time.sleep(1.5)
            click(continuePK_btn_pos)
        elif state == GameState.IN_MATCH:
            last_q_time = time.time() - 10000
            last_d_time = time.time() - 10000
            porgress_sc = capture_area(progress)
            progress_OCR = recognize_progress(porgress_sc)
            while progress_OCR[1] == 0:
                porgress_sc = capture_area(progress)
                progress_OCR = recognize_progress(porgress_sc)
                print("未找到正确的进度")
                time.sleep(0.1)
            current_progrss = 0
            last_result = None
            last_number = None
            next_res = None
            not_found = 0
            #做题部分！！
            while True:
                time_diff = time.time() - last_q_time
                last_q_time = time.time()
                if current_progrss == 30:
                    state = GameState.END_MATCH
                    break
                # porgress_sc = capture_area(progress)
                # progress_OCR = recognize_progress(porgress_sc)
                # if current_progrss == progress_OCR[0]:
                #     if time.time() - last_d_time > 1:
                #         print("重画")
                #         last_d_time = time.time()
                #         if last_result:
                #             draw_greater_than(draw_pos)
                #         else:
                #             draw_less_than(draw_pos)
                #         time.sleep(0.002)
                #     continue
                # if progress_OCR[1] == 0:
                #     print("进度识别失败")
                #     time.sleep(0.002)
                #     continue
                if next_res != None:
                    next_compare = compare_numbers(next_res)
                    if next_compare == None:
                        print("比较失败or速度保护")
                        time.sleep(0.002)
                        continue
                    
                    if next_compare:
                        draw_greater_than(draw_pos)
                        print("Preload Hit: {} > {}|耗时：{}".format(next_res[0], next_res[1], time_diff))
                    else:
                        draw_less_than(draw_pos)
                        print("Preload Hit: {} < {}|耗时：{}".format(next_res[0], next_res[1], time_diff))
                    #preload more
                    last_d_time = time.time()
                    next_sc = capture_area(next_que)
                    temp_next = recognize_numbers(next_sc)
                    if temp_next == next_res:
                        print("Preload Miss")
                        next_res = None
                    else:
                        next_res = temp_next
                    # Wait for all async tasks to finish
                    time.sleep(0.05)
                    continue
                
                
                question_sc = capture_area(question)
                number = recognize_numbers(question_sc)
                if number == last_number:
                    print("重复的题目")
                    time.sleep(0.2)
                    continue
                while number == None and not_found < 50:
                    not_found += 1
                    print("OCR题目失败|{}".format(not_found))
                    question_sc = capture_area(question)
                    number = recognize_numbers(question_sc)
                    time.sleep(0.002)
                if not_found >= 50:
                    state = GameState.END_MATCH
                    break
                else:
                    not_found = 0

                res_compare = compare_numbers(number)
                if res_compare == None:
                    print("比较失败")
                    time.sleep(0.002)
                    continue
                last_result = res_compare
                if res_compare:
                    draw_greater_than(draw_pos)
                    print("{} > {}|耗时：{}".format(number[0], number[1], time_diff))
                else:
                    draw_less_than(draw_pos)
                    print("{} < {}|耗时：{}".format(number[0], number[1], time_diff))
                # next_sc = capture_area(next_que)
                # number = recognize_numbers(next_sc)
                last_d_time = last_q_time
                if last_number != number:
                    last_number = number
                    current_progrss += 1
                #preload next question
                next_sc = capture_area(next_que)
                next_res = recognize_numbers(next_sc)

if __name__ == "__main__":
    # playground = locate_playground()
    # progress = playground[0]
    # question = playground[1]
    # windows_rect = playground[2]
    # phone = playground[3]
    # #增加偏移量
    # progress[0] += windows_rect[0]
    # progress[1] += windows_rect[1]
    # question[0] += windows_rect[0]
    # question[1] += windows_rect[1]
    # phone[0] += windows_rect[0]
    # phone[1] += windows_rect[1]
    # draw_pos = [phone[0] + int(phone[2] / 2), phone[1] + int(phone[3] / 2) + 50]
    # draw_less_than(draw_pos)
    


    # # reward_btn_pos = [phone[0] + int(phone[2] / 2), phone[1] + int(phone[3] / 2) + 180]
    # # continue_btn_pos = [phone[0] + int(phone[2] / 2) + 120, phone[1] + int(phone[3] / 2) + 480]
    # sc = capture_area(next_que)
    # number = recognize_numbers(sc)
    # print(number)
    # cv2.imshow("sc", sc)
    # cv2.waitKey(0)
    main()
    
    


    pass


