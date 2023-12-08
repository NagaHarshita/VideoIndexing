import pickle
import numpy as np
from scipy.signal import spectrogram
from pydub import AudioSegment
from scipy.ndimage import maximum_filter
import pandas as pd
from collections import defaultdict
import time

SAMPLE_RATE = 44100

PEAK_BOX_SIZE = 30

POINT_EFFICIENCY = 0.8

TARGET_START = 0.05

TARGET_T = 1.8

TARGET_F = 4000

FFT_WINDOW_SIZE = 0.2

DB_PATH = "./hash.db"


def my_spectrogram(audio):
    """Helper function that performs a spectrogram with the values in settings."""
    nperseg = int(SAMPLE_RATE * FFT_WINDOW_SIZE)
    return spectrogram(audio, SAMPLE_RATE, nperseg=nperseg)


def file_to_spectrogram(filename):
    """Calculates the spectrogram of a file.

    Converts a file to mono and resamples to :data:`~abracadabra.settings.SAMPLE_RATE` before
    calculating. Uses :data:`~abracadabra.settings.FFT_WINDOW_SIZE` for the window size.

    :param filename: Path to the file to spectrogram.
    :returns: * f - list of frequencies
              * t - list of times
              * Sxx - Power value for each time/frequency pair
    """
    a = AudioSegment.from_file(filename).set_channels(1).set_frame_rate(SAMPLE_RATE)
    audio = np.frombuffer(a.raw_data, np.int16)
    return my_spectrogram(audio)

def find_peaks(Sxx):
    """Finds peaks in a spectrogram.

    Uses :data:`~abracadabra.settings.PEAK_BOX_SIZE` as the size of the region around each
    peak. Calculates number of peaks to return based on how many peaks could theoretically
    fit in the spectrogram and the :data:`~abracadabra.settings.POINT_EFFICIENCY`.

    Inspired by
    `photutils
    <https://photutils.readthedocs.io/en/stable/_modules/photutils/detection/core.html#find_peaks>`_.

    :param Sxx: The spectrogram.
    :returns: A list of peaks in the spectrogram.
    """
    data_max = maximum_filter(Sxx, size=PEAK_BOX_SIZE, mode='constant', cval=0.0)
    peak_goodmask = (Sxx == data_max)  # good pixels are True
    y_peaks, x_peaks = peak_goodmask.nonzero()
    peak_values = Sxx[y_peaks, x_peaks]
    i = peak_values.argsort()[::-1]
    # get co-ordinates into arr
    j = [(y_peaks[idx], x_peaks[idx]) for idx in i]
    total = Sxx.shape[0] * Sxx.shape[1]
    # in a square with a perfectly spaced grid, we could fit area / PEAK_BOX_SIZE^2 points
    # use point efficiency to reduce this, since it won't be perfectly spaced
    # accuracy vs speed tradeoff
    peak_target = int((total / (PEAK_BOX_SIZE**2)) * POINT_EFFICIENCY)
    return j[:peak_target]

def idxs_to_tf_pairs(idxs, t, f):
    """Helper function to convert time/frequency indices into values."""
    return np.array([(f[i[0]], t[i[1]]) for i in idxs])


def hash_point_pair(p1, p2):
    """Helper function to generate a hash from two time/frequency points."""
    return hash((p1[0], p2[0], p2[1]-p2[1]))


def target_zone(anchor, points, width, height, t):
    """Generates a target zone as described in `the Shazam paper
    <https://www.ee.columbia.edu/~dpwe/papers/Wang03-shazam.pdf>`_.

    Given an anchor point, yields all points within a box that starts `t` seconds after the point,
    and has width `width` and height `height`.

    :param anchor: The anchor point
    :param points: The list of points to search
    :param width: The width of the target zone
    :param height: The height of the target zone
    :param t: How many seconds after the anchor point the target zone should start
    :returns: Yields all points within the target zone.
    """
    x_min = anchor[1] + t
    x_max = x_min + width
    y_min = anchor[0] - (height*0.5)
    y_max = y_min + height
    for point in points:
        if point[0] < y_min or point[0] > y_max:
            continue
        if point[1] < x_min or point[1] > x_max:
            continue
        yield point


def hash_points(points, filename):
    """Generates all hashes for a list of peaks.

    Iterates through the peaks, generating a hash for each peak within that peak's target zone.

    :param points: The list of peaks.
    :param filename: The filename of the song, used for generating song_id.
    :returns: A list of tuples of the form (hash, time offset, song_id).
    """
    hashes = []
    song_id = filename
    for anchor in points:
        for target in target_zone(
            anchor, points, TARGET_T, TARGET_F, TARGET_START
        ):
            hashes.append((
                # hash
                hash_point_pair(anchor, target),
                # time offset
                anchor[1],
                # filename
                song_id
            ))
    return hashes


def fingerprint_file(filename):
    """Generate hashes for a file.

    Given a file, runs it through the fingerprint process to produce a list of hashes from it.

    :param filename: The path to the file.
    :returns: The output of :func:`hash_points`.
    """
    f, t, Sxx = file_to_spectrogram(filename)
    peaks = find_peaks(Sxx)
    peaks = idxs_to_tf_pairs(peaks, t, f)
    return hash_points(peaks, filename)


def score_match(offsets):
    """Score a matched song.

    Calculates a histogram of the deltas between the time offsets of the hashes from the
    recorded sample and the time offsets of the hashes matched in the database for a song.
    The function then returns the size of the largest bin in this histogram as a score.

    :param offsets: List of offset pairs for matching hashes
    :returns: The highest peak in a histogram of time deltas
    :rtype: int
    """
    # Use bins spaced 0.5 seconds apart
    binwidth = 0.5
    tks = list(map(lambda x: x[0] - x[1], offsets))
    hist, _ = np.histogram(tks,
                           bins=np.arange(int(min(tks)),
                                          int(max(tks)) + binwidth + 1,
                                          binwidth))
    return np.max(hist)


def best_match(matches):
    """For a dictionary of song_id: offsets, returns the best song_id.

    Scores each song in the matches dictionary and then returns the song_id with the best score.

    :param matches: Dictionary of song_id to list of offset pairs (db_offset, sample_offset)
       as returned by :func:`~abracadabra.Storage.storage.get_matches`.
    :returns: song_id with the best score.
    :rtype: str
    """
    matched_song = None
    best_score = 0
    for song_id, offsets in matches.items():
        if len(offsets) < best_score:
            # can't be best score, avoid expensive histogram
            continue
        score = score_match(offsets)
        if score > best_score:
            best_score = score
            matched_song = song_id
    return matched_song

def get_matches(hashes):
    h_dict = {}
    for h, t, _ in hashes:
        h_dict[h] = t

    # in_values = f"({','.join([str(h[0]) for h in hashes])})"
    in_values = [(h[0]) for h in hashes]
    # print(in_values)
    query_hash = hash_dict[hash_dict['hash'].isin(in_values)]

    query_hash = query_hash.values.tolist()
    result_dict = defaultdict(list)
    for r in query_hash:
        result_dict[r[2]].append((r[1], h_dict[r[0]]))
    return result_dict


def recognise_song(filename):
    """Recognises a pre-recorded sample.

    Recognises the sample stored at the path ``filename``. The sample can be in any of the
    formats in :data:`recognise.KNOWN_FORMATS`.

    :param filename: Path of file to be recognised.
    :returns: :func:`~abracadabra.recognise.get_song_info` result for matched song or None.
    :rtype: tuple(str, str, str)
    """
    hashes = fingerprint_file(filename)
    matches = get_matches(hashes)
    matched_song = best_match(matches)
    return matched_song

pkl_file = 'hash.pkl'
start = time.time()
hash_dict = pd.read_pickle(pkl_file)
print(recognise_song("../../../queries/video" + "5" + "_1.wav"))
print(time.time()-start)