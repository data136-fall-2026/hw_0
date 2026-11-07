"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""

import uuid

from django.shortcuts import render, redirect
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest, JsonResponse)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from datetime import datetime
from django.views.decorators.http import require_GET, require_POST
import zoneinfo
import json
import io

# from app.models import InstructorProfile, StudentProfile

from .models import (InstructorProfile, StudentProfile, Course, Enrollment,
                      Lecture, QRCodeUpload, is_instructor, is_student)
# import getUploadsForCourse later

CDT = zoneinfo.ZoneInfo("America/Chicago")

# ---------------------------------------------------------------------------
# HW2  — index, time, sum
# ---------------------------------------------------------------------------

def index(request):
    """Render the home page (index.html) with current Chicago time and logged-in user."""
    current_time = datetime.now(CDT).strftime("%H:%M")
    context = {"time": current_time, "user": request.user}
    return render(request, 'app/index.html', context)


def time_view(request):
    """Return the current Chicago time as HH:MM."""
    time = datetime.now(zoneinfo.ZoneInfo("America/Chicago"))
    return HttpResponse(time.strftime("%H:%M"))

def sum_view(request):
    """Receives two numbers and returns sum."""
    a = float(request.GET.get('n1', 0))
    b = float(request.GET.get('n2', 0))
    total = a + b
    if total.is_integer():
        total = int(total)
    return HttpResponse(f"<p>{total}</p>")

# ---------------------------------------------------------------------------
# HW4  — user creation
# ---------------------------------------------------------------------------

# Display the form first 
@require_GET
def new(request):
    """Display the sign-up form, GET only."""
    return render(request, 'app/new.html')

@csrf_exempt
@require_POST
def createUser(request):
    """Create a new user."""
    user_name = request.POST.get('user_name', '')
    password = request.POST.get('password', '')
    email = request.POST.get('email', '')
    is_student = request.POST.get('is_student') == '1'
    if User.objects.filter(email=email).exists():
        return HttpResponseBadRequest("Email already exists.")
    if User.objects.filter(username=user_name).exists():
        return HttpResponseBadRequest("Username already exists.")
    user = User.objects.create_user(username=user_name, password=password, email=email)
    if is_student:
        StudentProfile.objects.create(user=user)
    else:
        InstructorProfile.objects.create(user=user)
    login(request, user)
    return HttpResponse("User successfully created", status=200)

# ---------------------------------------------------------------------------
# HW5  — courses, lectures, QR uploads, dump
# ---------------------------------------------------------------------------

def new_course(request):
    """Display the form to create a new course."""
    return render(request, 'app/new_course.html')

def new_lecture(request):
    """Display the form to create a new lecture."""
    if is_instructor(request.user):
        courses = Course.objects.filter(instructor__user=request.user)
    else:
        courses = []
    return render(request, 'app/new_lecture.html', {'courses': courses})

def new_qr_upload(request):
    """Display the QR code upload form."""
    return render(request, 'app/new_qr_upload.html')

DAYS = [("day-mon", "M"), ("day-tue", "T"), ("day-wed", "W"),
        ("day-thu", "R"), ("day-fri", "F")]

@csrf_exempt
@require_POST
def createCourse(request):
    """Create a new course."""
    if not is_instructor(request.user):
        return HttpResponse("Only instructors can create courses.", status=401)
    instructor_profile = InstructorProfile.objects.get(user=request.user)

    course_name = request.POST.get('course-name', '')
    meeting_days = "".join(code for field, code in DAYS if field in request.POST)
    start_time = request.POST.get('start-time', '')
    end_time = request.POST.get('end-time', '')

    if not course_name or not meeting_days or not start_time or not end_time:
        return HttpResponseBadRequest("All fields are required.")

    if Course.objects.filter(name=course_name).exists():
        return HttpResponseBadRequest("Course already exists.")

    # Create the course
    course = Course.objects.create(
        name=course_name,
        instructor=instructor_profile,
        meeting_days=meeting_days,
        time_start=start_time,
        time_end=end_time
    )
    return HttpResponse(f"Course '{course.name}' created successfully.", status=200)

@csrf_exempt
@require_POST
def createLecture(request):
    """Create a new lecture."""
    if not is_instructor(request.user):
        return HttpResponse("Only instructors can create lectures.", status=401)

    course = Course.objects.filter(name=request.POST.get("choice")).first()
    if course is None:
        return HttpResponse("Course does not exist.", status=400)

    Lecture.objects.create(
        course=course,
        lecture_date=datetime.now(CDT),
        qr_code=uuid.uuid4().hex
    )
    return HttpResponse(f"Lecture created successfully.", status=200)

@csrf_exempt
@require_POST
def createQRCodeUpload(request):
    """Upload a QR code."""
    if not is_student(request.user):
        return HttpResponse("Only students can upload QR codes.", status=401)
    student_profile = StudentProfile.objects.get(user=request.user)

    image = request.FILES.get('imageUpload')
    if image is None:
        return HttpResponse("No file uploaded.", status=400)

    QRCodeUpload.objects.create(
        student=student_profile,
        file=image,
        upload_timestamp=datetime.now(CDT)
    )
    return HttpResponse(f"QR code uploaded successfully.", status=200)

@csrf_exempt
@require_GET
def dumpUploads(request):
    """List all the uploaded QR files (JSON)."""
    if not is_instructor(request.user):
        return HttpResponse("Only instructors can view uploads.", status=401)

    data = []
    for upload in QRCodeUpload.objects.all():
        data.append({
            "username": upload.student.user.username,
            "upload_time": upload.upload_timestamp.astimezone(CDT).strftime("%Y-%m-%d %H:%M:%S")
        })

    return JsonResponse(data, safe=False)


# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



