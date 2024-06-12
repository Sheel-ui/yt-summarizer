from django.shortcuts import render
from django.views.decorators.http import require_http_methods
import re
from pytube import YouTube
from pytube.exceptions import VideoUnavailable
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import io
from django.http import HttpResponse

def is_valid_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    youtube_regex_match = re.match(youtube_regex, url)
    if youtube_regex_match:
        try:
            video_id = youtube_regex_match.group(6)
            YouTube(url)  # This checks if the video is accessible
            return video_id
        except VideoUnavailable:
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    else:
        return None
    
def fetch_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def create_srt(transcript):
    srt_content = ""
    for i, entry in enumerate(transcript):
        start = entry['start']
        duration = entry.get('duration', 0)
        end = start + duration
        srt_content += f"{i + 1}\n{format_time(start)} --> {format_time(end)}\n{entry['text']}\n\n"
    return srt_content

def format_time(seconds):
    ms = int((seconds % 1) * 1000)
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def home(request):
    return render(request, 'home/index.html')

@require_http_methods(['POST'])
def submit(request):
    url = request.POST.get('url','')
    video_id = is_valid_youtube_url(url)
    if video_id:
        return render(request,'home/partials/preview.html',{"video_id":video_id})
    else:
        return HttpResponse("Invalid YouTube URL")
    


@require_http_methods(['GET'])
def download_file(request, file_type, video_id):
    transcript = fetch_transcript(video_id)
    if not transcript:
        return HttpResponse("No transcript available for download.", status=404)
    
    if file_type == 'srt':
        srt_content = create_srt(transcript)
        response = HttpResponse(io.BytesIO(srt_content.encode()), content_type='text/srt')
        response['Content-Disposition'] = f'attachment; filename="{video_id}.srt"'
        return response
    elif file_type == 'txt':
        txt_content = "\n".join([entry['text'] for entry in transcript])
        response = HttpResponse(io.BytesIO(txt_content.encode()), content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{video_id}.txt"'
        return response
    else:
        return HttpResponse("Invalid file type.", status=400)
    

@require_http_methods(['POST'])
def generate(request,video_id):
    transcript = fetch_transcript(video_id)
    return render(request,'home/partials/content.html',{"content": transcript})
    