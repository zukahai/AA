from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
import argparse
import facenet
import os
import sys
import math
import pickle
import align.detect_face
import numpy as np
import cv2
import collections
from sklearn.svm import SVC
import requests
import json
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', help='Path of the video you want to test on.', default=0)
    args = parser.parse_args()
    
    # Cai dat cac tham so can thiet
    MINSIZE = 20
    THRESHOLD = [0.6, 0.7, 0.7]
    FACTOR = 0.709
    IMAGE_SIZE = 182
    INPUT_IMAGE_SIZE = 160
    CLASSIFIER_PATH = 'Models/facemodel.pkl'
    VIDEO_PATH = args.path
    FACENET_MODEL_PATH = 'Models/20180402-114759.pb'

    # Load model da train de nhan dien khuon mat - thuc chat la classifier
    with open(CLASSIFIER_PATH, 'rb') as file:
        model, class_names = pickle.load(file)
    print("Custom Classifier, Successfully loaded")

    with tf.Graph().as_default():

        # Cai dat GPU neu co
        gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
        sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))

        with sess.as_default():

            # Load model MTCNN phat hien khuon mat
            print('Loading feature extraction model')
            facenet.load_model(FACENET_MODEL_PATH)

            # Lay tensor input va output
            images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
            embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
            phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
            embedding_size = embeddings.get_shape()[1]

            # Cai dat cac mang con
            pnet, rnet, onet = align.detect_face.create_mtcnn(sess, "src/align")

            people_detected = set()
            person_detected = collections.Counter()
            #-----------------------------------------
            faceCofirm = {}
            ipAddress = "192.168.2.76"
            numGetSimple = 5
            userId={
                "sy":123,
                "anh":1234,
                "nghia":121
            }
            best_name = None
            #-----------------------------------------
            # Lay hinh anh tu file video
            cap = cv2.VideoCapture(VIDEO_PATH)
            while (cap.isOpened()):
                # Doc tung frame
                ret, frame = cap.read()

                # Phat hien khuon mat, tra ve vi tri trong bounding_boxes
                bounding_boxes, _ = align.detect_face.detect_face(frame, MINSIZE, pnet, rnet, onet, THRESHOLD, FACTOR)

                faces_found = bounding_boxes.shape[0]
                try:
                    # Neu co it nhat 1 khuon mat trong frame
                    if faces_found > 0:
                        det = bounding_boxes[:, 0:4]
                        bb = np.zeros((faces_found, 4), dtype=np.int32)
                        for i in range(faces_found):
                            bb[i][0] = det[i][0]
                            bb[i][1] = det[i][1]
                            bb[i][2] = det[i][2]
                            bb[i][3] = det[i][3]

                            # Cat phan khuon mat tim duoc
                            cropped = frame[bb[i][1]:bb[i][3], bb[i][0]:bb[i][2], :]
                            scaled = cv2.resize(cropped, (INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE),
                                                interpolation=cv2.INTER_CUBIC)
                            scaled = facenet.prewhiten(scaled)
                            print(len(scaled[0])) #show metric face
                            scaled_reshape = scaled.reshape(-1, INPUT_IMAGE_SIZE, INPUT_IMAGE_SIZE, 3)
                            feed_dict = {images_placeholder: scaled_reshape, phase_train_placeholder: False}
                            emb_array = sess.run(embeddings, feed_dict=feed_dict)
                            
                            # Dua vao model de classifier
                            predictions = model.predict_proba(emb_array)
                            # print(emb_array)
                            best_class_indices = np.argmax(predictions, axis=1)
                            best_class_probabilities = predictions[
                                np.arange(len(best_class_indices)), best_class_indices]
                            
                            # Lay ra ten va ty le % cua class co ty le cao nhat
                            best_name = class_names[best_class_indices[0]]

                            print("Name: {}, Probability: {}".format(best_name, best_class_probabilities))

                            # Ve khung mau xanh quanh khuon mat
                            cv2.rectangle(frame, (bb[i][0], bb[i][1]), (bb[i][2], bb[i][3]), (0, 255, 0), 2)
                            text_x = bb[i][0]
                            text_y = bb[i][3] + 20
                            if faceCofirm.get(best_name) == None:
                                faceCofirm[best_name] = 0
                            # Neu ty le nhan dang > 0.5 thi hien thi ten
                            if best_class_probabilities > 0.7:
                                name = class_names[best_class_indices[0]]
                                
                                faceCofirm[name] = faceCofirm[name] +1
                                print(name,faceCofirm[name])
                            else:
                                # Con neu <=0.5 thi hien thi Unknow
                                name = "Unknown"
                                
                            # Viet text len tren frame    
                            cv2.putText(frame, name, (text_x, text_y), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                        1, (255, 255, 255), thickness=1, lineType=2)
                            cv2.putText(frame, str(round(best_class_probabilities[0], 3)), (text_x, text_y + 17),
                                        cv2.FONT_HERSHEY_COMPLEX_SMALL,
                                        1, (255, 255, 255), thickness=1, lineType=2)
                            person_detected[best_name] += 1
                    #-----------------------------payable---------------------------
                    width = int(frame.shape[1])
                    height = int(frame.shape[0])
                    
                    if faceCofirm.get(best_name) >= numGetSimple:
                        frame = cv2.imread("./src/image/pay.jpg")
                        dim = (width, height)
                        frame = cv2.resize(frame, dim, interpolation = cv2.INTER_AREA)
                        # print(frame.shape)
                        id_ = userId.get(best_name)
                        text = requests.get("http://{}/web_mvc/payment-pro.php?id={}".format(ipAddress,id_)).text
                        cv2.putText(frame, best_name, (0, 50), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                            2, (255, 0, 0), thickness=1, lineType=2)
                        cv2.putText(frame, str(text) , (0, 100), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                            1.3, (255, 0, 0), thickness=1, lineType=2)
                    else:
                        cv2.putText(frame, "wait take simple", (0, 50), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                            2, (255, 0, 0), thickness=1, lineType=2)
                        
                            
                    #---------------------------------------------------------------

                except:
                    pass

                # Hien thi frame len man hinh
                cv2.imshow('Face Recognition', frame)
                try:
                    if int(faceCofirm.get(best_name)) > numGetSimple:
                        time.sleep(3)
                        faceCofirm = {}
                except:
                    pass
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            cap.release()
            cv2.destroyAllWindows()


main()
