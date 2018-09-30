import scipy.io as sio
import numpy as np
import pdb
from itertools import groupby
import operator as op
import pprint

NUM_PIDS = 7141

CAM_IDX = 0
PER_IDX = 1
FRM_IDX = 2

DIV_ONE = 108980
DIV_TWO = 168260

# Return string camera id for camera idx
def cstr(i):
	if i < 8:
		return '%d' % i
	else:
		return 'x'


A = sio.loadmat('ground_truth/trainval')
A = A['trainData']

print("Train data shape:")
print(np.shape(A))

# build histogram
x_edges = range(1, 10, 1)
y_edges = range(1, NUM_PIDS + 1, 1)

hist = np.histogram2d(A[:, CAM_IDX], A[:, PER_IDX], bins=(x_edges, y_edges))
# print(hist)

# frame offets (from http://vision.cs.duke.edu/DukeMTMC/details.html)
cam_offsets = [5542, 3606, 27243, 31181, 0, 22401, 18967, 46765]
num_cams = len(cam_offsets)

# adjust frame #s
for i in range(0, np.shape(A)[0]):
	cam_id = (int)(A[i][CAM_IDX]) - 1
	A[i][FRM_IDX] += cam_offsets[cam_id]

# sort by frame # (camera id)
A = A[np.lexsort((A[:, CAM_IDX], A[:, FRM_IDX],))]

# extract segments
idx = A[:, FRM_IDX]
A_1 = A[idx < DIV_ONE]
A_2 = A[(idx < DIV_TWO) & (idx >= DIV_ONE)]
A_3 = A[idx >= DIV_TWO]

print("Frame range: ")
print(A[0, FRM_IDX], A[-1, FRM_IDX])
frames_ct = [[0, 0, 0] for i in range(0, 8)]
for i in range(0, np.shape(A)[0]):
	fid = int(A[i][FRM_IDX])
	cid = int(A[i][CAM_IDX]) - 1
	if fid < DIV_ONE:
		frames_ct[cid][0] += 1
	elif fid < DIV_TWO:
		frames_ct[cid][1] += 1
	else:
		frames_ct[cid][2] += 1
print("Detections in [16.5 min periods]: ")
print(frames_ct)

# build people list
people = [[] for i in range(0, NUM_PIDS)]

for i in range(0, np.shape(A)[0]):
	people[(int)(A[i][PER_IDX])].append(A[i][CAM_IDX])

# group by camera id
for i in range(0, len(people)):
	people[i] = [x[0] for x in groupby(people[i])]

# print(people)

# find most popular trajectories
trajs = {}

for i in range(0, len(people)):
	t = tuple(people[i])
	if t in trajs:
		trajs[t] += 1
	else:
		trajs[t] = 1

trajs = sorted(trajs.items(), key=op.itemgetter(1), reverse=True)

print("Most popular trajectories:")
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(trajs[:11])

# compute camera matrix
matrix = np.zeros((num_cams, num_cams + 1))

for i in range(0, len(people)):
	for j in range(0, len(people[i])):
		cam_1 = (int)(people[i][j]) - 1
		if j == len(people[i]) - 1:
			matrix[cam_1][num_cams] += 1
			continue
		cam_2 = (int)(people[i][j+1]) - 1
		matrix[cam_1][cam_2] += 1

print("Frequency matrix:")
print(matrix)

# build people list, II
people = [[] for i in range(0, NUM_PIDS)]

for i in range(0, np.shape(A)[0]):
	people[(int)(A[i][1])].append(A[i])

# check # frames in cam / # frames in traj
frames_in_cam = [0. for i in range(0, NUM_PIDS)]
frames_total = [0. for i in range(0, NUM_PIDS)]

for i in range(0, len(people)):
	p = people[i]
	if len(p) == 0:
		continue
	# frames in traj (total)
	frames_total[i] = p[-1][FRM_IDX] - p[0][FRM_IDX]
	# frames in cam
	for j in range(1, len(p)):
		if p[j][CAM_IDX] == p[j-1][CAM_IDX]:
			frames_in_cam[i] += (p[j][FRM_IDX] - p[j-1][FRM_IDX])

print("Frac. frames in cam (overall):")
print("%0.6f" % (sum(frames_in_cam) / sum(frames_total)))

# compute camera matrix_t
times = [0.1, 0.2, 0.5, 1.0, 2.0, 10.0, 90.0]
fpm = 60 * 60
matrix_t = np.zeros((len(times), num_cams, num_cams + 1))

arrivals_t = [[[] for i in range(0, num_cams + 1)] for i in range(0, num_cams)]

for i in range(0, len(people)):
	for j in range(0, len(people[i])):
		cam_1 = (int)(people[i][j][CAM_IDX]) - 1
		if j == (len(people[i]) - 1):
			for idx, _ in enumerate(times):
				matrix_t[idx][cam_1][num_cams] += 1
			continue
		cam_2 = (int)(people[i][j+1][CAM_IDX]) - 1
		if cam_1 == cam_2:
			continue
		frame_1 = people[i][j][FRM_IDX]
		frame_2 = people[i][j+1][FRM_IDX]
		for idx, t in enumerate(times):
			if frame_2 - frame_1 < (fpm * t):
				matrix_t[idx][cam_1][cam_2] += 1
		arrivals_t[cam_1][cam_2].append((frame_2 - frame_1) / 60.);

matrix_t_n = np.zeros(np.shape(matrix_t))

# print('\nFrequency matrices:')
for i in range(0, len(matrix_t)):
	# print('Time (min.): ', times[i])
	np.set_printoptions()
	# print(matrix_t[i])
	for j in range(0, len(matrix_t[i])):
		row_sum = sum(matrix_t[i][j])
		if row_sum != 0:
			matrix_t_n[i][j] = matrix_t[i][j] / row_sum
			matrix_t_n[i][j] *= 100.
	np.set_printoptions(formatter={'float': lambda x: "%06s" % "{0:2.2f}".format(x)})
	# print(matrix_t_n[i])

# print temporal progressions
print('\nTraffic dest. distributions:')
print('Times (min.): ', times)
for i in range(0, num_cams):
	print('')
	for j in range(0, num_cams + 1):
		if matrix_t_n[-1, i, j] >= 10.0:
			print('cam %s -> %s: ' % (cstr(i), cstr(j)), matrix_t_n[:, i, j])

# print arrival histograms
bins = [0, 10, 20, 30, 60, 120, 500, 5400]
print('\nArrival time histograms:')
print('Times (sec.): ', bins)
for i in range(0, num_cams):
	print('')
	for j in range(0, num_cams):
		if matrix_t_n[-1, i, j] >= 0.0:
			hist, bins = np.histogram(sorted(arrivals_t[i][j]), bins=bins)
			print('cam %s -> %s: ' % (cstr(i), cstr(j)), hist / (1.e-8 + sum(hist)))
