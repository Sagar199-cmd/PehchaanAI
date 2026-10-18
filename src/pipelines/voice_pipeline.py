from resemblyzer import VoiceEncoder , preprocess_wav

import numpy as np
import io
import librosa
import streamlit as st

@st.cache_resource
def load_voice_encoder():
  return VoiceEncoder()
# load voice encoder

def get_voice_embedding(audio_bytes):

  try:
    encoder = load_voice_encoder()

    audio , sr = librosa.load(io.BytesIO(audio_bytes),sr=16000)
    # librosa return 2 things audio and sample rate(sr)
    # higher value of sr means higher quality of audio but here for human voice 16000 is enough for loading

    wav = preprocess_wav(audio)
    # preprocess audio remove noise

    embedding  = encoder.embed_utterance(wav)

    return embedding.tolist()
    # 256 dim vector of embeddings

  except Exception as e:
    st.error("Voice recognition error")
    return None


def identify_speaker(new_embedding , candidates_dict , threshold = 0.65):
  if new_embedding is None or not  candidates_dict :
    return None , 0.0

  best_sid = None
  best_score = -1.0

  for sid , stored_embedding in candidates_dict.items():
    if stored_embedding:
      similarity = np.dot(new_embedding,stored_embedding)
      # Cal similarity between 2 embeddings using dot product
      if similarity > best_score:
        best_score = similarity
        best_sid = sid

  if best_score >= threshold:
    return best_sid,best_score

  return None , best_score


# catching voice all students from bulk audio
def process_bulk_audio(audio_bytes,candidates_dict, threshold = 0.65):
  try:
    encoder = load_voice_encoder()

    audio ,sr = librosa.load(io.BytesIO(audio_bytes),sr=16000)

    segments = librosa.effects.split(audio , top_db=30)
    # divide audio into segments , here top_db control sensitivity of audio means if top_db value is very high it only catch loud voice

    identified_results = {}

    for start,end in segments:
      if(end - start) < sr * 0.5:
        continue
       # remove segment which have voices which are low ,thrash , noise 

      segment_audio = audio[start:end]
      wav = preprocess_wav(segment_audio)
      embedding = encoder.embed_utterance(wav)

      sid ,score = identify_speaker(embedding,candidates_dict,threshold)
      # check if this segment embedding matches with any student

      # if matches
      if sid:
        if sid not in identified_results or score > identified_results[sid]:
          identified_results[sid] = score 
        # if that student is not present in result dict or if present but cur score is better than stored then insert/update it

    return identified_results
  except Exception as e:
    st.error('Bulk process error')
    return {}



      


  


