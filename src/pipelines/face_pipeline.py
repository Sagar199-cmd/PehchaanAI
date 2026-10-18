import streamlit as st
import dlib
import face_recognition_models
from sklearn.svm import SVC
import numpy as np

from src.database.db import get_all_students

@st.cache_resource #it ensure face model load once not again and again
def load_dlib_models():
  detector = dlib.get_frontal_face_detector() #detect no of faces and draw rectangle

  sp = dlib.shape_predictor(
    face_recognition_models.pose_predictor_model_location()
  )
  #find landmarks on the face

  facerec = dlib.face_recognition_model_v1(
    face_recognition_models.face_recognition_model_location()
  )
  # find 128 dim embeddings of the image

  return detector , sp , facerec 

def get_face_embeddings(image_np):
  detector , sp ,facerec = load_dlib_models()
  faces = detector(image_np,1)
  # 1 - means rotate , twist, image only 1 time to analyze no of faces
  embeddings = []
  for face in faces:
    shape= sp(image_np,face) # find landmarks of face in image 
    face_descriptor = facerec.compute_face_descriptor(image_np,shape,1) #find embeddings 128 dimension

    embeddings.append(np.array(face_descriptor)) 

  return embeddings

@st.cache_resource
def get_trained_model():
  X = []
  Y = []

  student_db = get_all_students()

  if not student_db:
    return None

  for student in student_db:
    embedding = student.get('face_embedding')
    if embedding:
      X.append(np.array(embedding))
      Y.append(student.get('student_id'))

  if len(X)==0:
    return 0

  clf = SVC(kernel='linear',probability=True , class_weight='balanced')

  try:
    clf.fit(X,Y)
  except ValueError:
    pass

  return {'clf':clf , 'X':X,'Y':Y}
#returning classifier model , X and Y

def train_classifier():
  st.cache_resource.clear()
  model_data = get_trained_model()
  return bool(model_data)
#when new student register then we will clear cache of already trained model and retrain it

def predict_attendance(class_image_np):
    embeddings = get_face_embeddings(class_image_np)
    # get embeddings of clicked grp photo
    detected_student={}

    model_data = get_trained_model()
    #load the model

    if not model_data:
      return detected_student , [] ,len(embeddings)
    # return everything empty is no model data is there

    clf = model_data['clf']
    x_train = model_data['X']
    y_train = model_data['Y']
    # extract model,x_train - embeddings ,y_train-student_id from model_data

    all_students = sorted(list(set(y_train)))
    #sorted and unique list of all registered students in db

    for embedding in embeddings:
      best_match_score = float('inf')
      predicted_id = None
        
      for i, student_embedding in enumerate(x_train):
          score = np.linalg.norm(student_embedding - embedding)
           # cal dist between them using linear algebra(actual student face emb and predicted embedding)
          # cal sqrt(sqaure of each elem of array come after subtracting stud embedding - embedding)
          if score < best_match_score:
              best_match_score = score
              predicted_id = y_train[i]

      resemblance_threshold = 0.6

      if predicted_id is not None and best_match_score <= resemblance_threshold:
            detected_student[predicted_id] = True

    return detected_student , all_students , len(embeddings)


         


  