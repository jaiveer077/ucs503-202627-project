"""
Face detection + matching, isolated in its own module so the rest of the
backend can keep running even if face_recognition/dlib isn't installed yet
(it needs a C++ compiler to build on first install, which can be flaky on
Windows - see backend README for the recommended conda-based install).
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

try:
    import face_recognition
    FACE_MATCHING_AVAILABLE = True
except ImportError:
    FACE_MATCHING_AVAILABLE = False

# How close two faces' encodings must be to count as a match.
# face_recognition's own default is 0.6 - lower = stricter matching.
MATCH_THRESHOLD = float(os.environ.get("FACE_MATCH_THRESHOLD", "0.6"))
if not 0 < MATCH_THRESHOLD < 1:
    raise ValueError("FACE_MATCH_THRESHOLD must be between 0 and 1")
MAX_IMAGE_DIMENSION = 2000


def _load_rgb_array(path):
    """
    Loads an image and guarantees it comes out as a clean 8-bit RGB numpy
    array. face_recognition's own load_image_file() usually does this,
    but some real-world photos (iPhone photos with a color profile, PNGs
    with transparency, CMYK JPEGs from certain editors) slip through as
    something dlib rejects with "Unsupported image type, must be 8bit
    gray or RGB image." Pillow normalizes their color and orientation;
    OpenCV shrinks very large images to bound scan time and memory use.
    """
    import cv2
    import numpy as np
    from PIL import Image, ImageOps

    # Pillow fixes orientation and converts to RGB; OpenCV only resizes large images.
    with Image.open(path) as source:
        img = ImageOps.exif_transpose(source).convert("RGB")
        rgb = np.asarray(img, dtype=np.uint8)
    height, width = rgb.shape[:2]
    if max(height, width) > MAX_IMAGE_DIMENSION:
        scale = MAX_IMAGE_DIMENSION / max(height, width)
        rgb = cv2.resize(rgb, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
    return np.ascontiguousarray(rgb)


def encode_faces_in_image(path):
    """
    Returns a list of 128-number face "encodings", one per face found in
    the image at `path`. A photo of a group of people returns multiple
    encodings; a photo with no detectable face returns an empty list.
    """
    if not FACE_MATCHING_AVAILABLE:
        raise RuntimeError("face_recognition is not installed")

    image = _load_rgb_array(path)
    locations = face_recognition.face_locations(image)
    encodings = face_recognition.face_encodings(image, known_face_locations=locations)
    return [enc.tolist() for enc in encodings]


def best_distance(reference_encoding, candidate_encodings):
    """
    Smallest face distance between the reference face and any of the
    candidate faces (0 = identical, higher = less alike), or None if
    there are no candidates to compare against.
    """
    if not FACE_MATCHING_AVAILABLE or not candidate_encodings:
        return None

    import numpy as np

    reference = np.array(reference_encoding)
    candidates = np.array(candidate_encodings)
    distances = face_recognition.face_distance(candidates, reference)
    return float(min(distances))


def distance_to_confidence(distance):
    # Simple, display-friendly conversion - not a calibrated probability,
    # just "closer distance = higher shown confidence".
    return round(max(0.0, 1 - distance), 2)


def best_match_confidence(reference_encoding, candidate_encodings):
    """
    Returns the best confidence score, or None if nothing is close
    enough (within MATCH_THRESHOLD) to count as a match.
    """
    distance = best_distance(reference_encoding, candidate_encodings)
    if distance is None or distance > MATCH_THRESHOLD:
        return None
    return distance_to_confidence(distance)
