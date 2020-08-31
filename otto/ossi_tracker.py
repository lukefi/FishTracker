import numpy as np
import os
from sort import Sort
import time
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

file_name = '2019-07-02_205000'
total_time = 0.0
total_frames = 0
max_age = 20
min_hits = 3
iou_threshold = 0.1
colours = np.random.rand(32, 3) #used only for display
plt.ion()
fig = plt.figure()
ax1 = fig.add_subplot(111)
ax1.axis('square')
if not os.path.exists('output'):
    os.makedirs('output')

mot_tracker = Sort(max_age=max_age, 
                    min_hits=min_hits,
                    iou_threshold=iou_threshold) #create instance of the SORT tracker


with open('luke_data/%s'%(file_name),'r') as in_file:
    lines = in_file.readlines()

def process(line):
    splitted = line.split('  ')
    timestamp = float(splitted[0].split(' ')[0])
    if len(splitted)>1:
        values = splitted[1].split(' ')
        if len(values)>0:
            del values[::3]
        values = [float(x) for x in values]
        values.insert(0,timestamp)
        return values
    else:
        return [timestamp]

data = list(map(lambda x: process(x),lines))

with open('output/%s.txt'%(file_name),'w') as out_file:
    print("Processing %s."%(file_name))
    for frame in range(len(data)):
        dets = data[frame][1:]
        # mock bounding box
        detections = np.array(dets)
        detections = detections.reshape((detections.shape[0]//2,2))
        detections = np.hstack([detections,np.zeros_like(detections)])
        detections[:,2] = detections[:,0]+50
        detections[:,3] = detections[:,1]+50
        total_frames += 1

        start_time = time.time()
        trackers = mot_tracker.update(detections)
        cycle_time = time.time() - start_time
        total_time += cycle_time

        for d in trackers:
            #print('%d,%d,%.2f,%.2f,%.2f,%.2f,1,-1,-1,-1'%(frame,d[4],d[0],d[1],d[2]-d[0],d[3]-d[1]),file=out_file)
            d[[0,2]] /= 100
            #d = d.astype(np.int32)
            #print(d)
            ax1.scatter(d[0],d[1],s=30,color=colours[int(d[4])%32],marker='X')
            plt.plot(detections[:,0]/100,detections[:,1],color='grey')
            #ax1.add_patch(patches.Rectangle((d[0],d[1]),d[2]-d[0],d[3]-d[1],fill=False,lw=3,ec=colours[d[4]%32,:]))
        for tracker in mot_tracker.trackers:
            history = np.array(tracker.history)
            if history.shape[0] ==0:
                continue
            #print(history.shape)
            history = history[:,0,:]
            history[:,[0,2]] /= 100
            ax1.scatter(history[:,0],history[:,1],s=10,color='grey')

        plt.scatter(detections[:,0]/100,detections[:,1],s=20,color='red',marker='x')
        ax1.set_xlim(xmin=0,xmax=100)
        ax1.set_ylim(ymin=0,ymax=50)
        fig.canvas.flush_events()
        plt.draw()
        plt.savefig('output_imgs/img_%04i.png'%frame)
        ax1.cla()
        time.sleep(0.05)

print("Total Tracking took: %.3f seconds for %d frames or %.1f FPS" % (total_time, total_frames, total_frames / total_time))

