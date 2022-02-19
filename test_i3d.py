import math
import os
import argparse
import pickle

import matplotlib.pyplot as plt

import torch
import torch.nn as nn

from torchvision import transforms
import videotransforms

import numpy as np

import torch.nn.functional as F
from pytorch_i3d import InceptionI3d

# from nslt_dataset_all import NSLT as Dataset
#from datasets.nslt_dataset_all import NSLT as Dataset
from datasets.nslt_dataset import NSLT as Dataset
import cv2
#os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
#os.environ["CUDA_VISIBLE_DEVICES"] = '0'


def load_rgb_frames_from_video(video_path, start=0, num=-1):
    vidcap = cv2.VideoCapture(video_path)
    # vidcap = cv2.VideoCapture('/home/dxli/Desktop/dm_256.mp4')

    frames = []

    vidcap.set(cv2.CAP_PROP_POS_FRAMES, start)
    if num == -1:
        num = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))

    for offset in range(num):
        success, img = vidcap.read()

        ## New - get out of loop if we have finished
        if success == False:
            break
        w, h, c = img.shape
        sc = 224 / w
        img = cv2.resize(img, dsize=(0, 0), fx=sc, fy=sc)

        img = (img / 255.) * 2 - 1

        frames.append(img)

    return torch.Tensor(np.asarray(frames, dtype=np.float32))


def run(mode='rgb',
        root='/ssd/Charades_v1_rgb',
        train_split='charades/charades.json',
        datasets=None,
        weights=None,
        num_classes=2000):
    with open("predictions.txt","w") as f:
        f.write('')
    f.close()
    # setup dataset
    test_transforms = transforms.Compose([videotransforms.CenterCrop(224)])

    if datasets is None:
        val_dataset = Dataset(train_split, 'test', root, mode, test_transforms)
    else:
        val_dataset = datasets['test']
    
    ## Change num_workers=0 - Docker bug        
    val_dataloader = torch.utils.data.DataLoader(val_dataset, batch_size=1,
                                                 shuffle=False, num_workers=0,
                                                 pin_memory=False)
    dataloaders = {'test': val_dataloader}
    datasets = {'test': val_dataset}

    # setup the model
    if mode == 'flow':
        i3d = InceptionI3d(400, in_channels=2)
        i3d.load_state_dict(torch.load('weights/flow_imagenet.pt',map_location='cpu'))
    else:
        i3d = InceptionI3d(400, in_channels=3)
        i3d.load_state_dict(torch.load('weights/rgb_imagenet.pt',map_location='cpu'))
        
    i3d.replace_logits(num_classes)
    i3d.load_state_dict(torch.load(weights,map_location='cpu'))  # nslt_2000_000700.pt nslt_1000_010800 nslt_300_005100.pt(best_results)  nslt_300_005500.pt(results_reported) nslt_2000_011400
    #i3d.cuda()
    i3d = nn.DataParallel(i3d)
    i3d.eval()

    correct = 0
    correct_5 = 0
    correct_10 = 0

    ## Bug fix - must be float since integer division will create integer values
    top1_fp = np.zeros(num_classes, dtype=np.float)
    top1_tp = np.zeros(num_classes, dtype=np.float)

    top5_fp = np.zeros(num_classes, dtype=np.float)
    top5_tp = np.zeros(num_classes, dtype=np.float)

    top10_fp = np.zeros(num_classes, dtype=np.float)
    top10_tp = np.zeros(num_classes, dtype=np.float)

    for c, data in enumerate(dataloaders["test"], 1):
        inputs, labels, video_id = data  # inputs: b, c, t, h, w

        per_frame_logits = i3d(inputs) # 1 x num_classes x num_frames
        
        ## 1 x num_classes
        predictions = torch.max(per_frame_logits, dim=2)[0]
        # predictions[0] --> num_classes tensor
        # lowest as the first element - highest as the last element
        out_labels = np.argsort(predictions.cpu().detach().numpy()[0])
        print(out_labels[-1])
        with open('predictions.txt','a') as f:
            f.write(str(out_labels[-1]))
            f.write('\n')
        f.close()
        out_probs = np.sort(predictions.cpu().detach().numpy()[0])

        lbl = labels[0][0].item()
        if lbl in out_labels[-5:]:
            correct_5 += 1
            top5_tp[lbl] += 1
        else:
            top5_fp[lbl] += 1
        if lbl in out_labels[-10:]:
            correct_10 += 1
            top10_tp[lbl] += 1
        else:
            top10_fp[lbl] += 1
        if torch.argmax(predictions[0]).item() == lbl:
            correct += 1
            top1_tp[lbl] += 1
        else:
            top1_fp[lbl] += 1

        print(str(c) + ' / ' + str(len(dataloaders['test'])), video_id[0], float(correct) / len(dataloaders["test"]), float(correct_5) / len(dataloaders["test"]),
              float(correct_10) / len(dataloaders["test"]))

        # per-class accuracy
    # if sum(top1_tp+top1_fp) == 0:
    #     print('sum is zeo')
    
    # Fix divide by zero error
    sum1 = top1_tp + top1_fp
    sum5 = top5_tp + top5_fp
    sum10 = top10_tp + top10_fp

    sum1[sum1 == 0] = 1e-10
    #top1_tp[sum1 == 0] = 0

    sum5[sum5 == 0] = 1e-10
    #top5_tp[sum5 == 0] = 0

    sum10[sum10 == 0] = 1e-10
    #top10_tp[sum10 == 0] = 0      

    top1_per_class = np.mean(top1_tp / sum1)
    top5_per_class = np.mean(top5_tp / sum5)
    top10_per_class = np.mean(top10_tp / sum10)
    print('top-k average per class acc: {}, {}, {}'.format(top1_per_class, top5_per_class, top10_per_class))


def ensemble(mode, root, train_split, weights, num_classes):
    # setup dataset
    test_transforms = transforms.Compose([videotransforms.CenterCrop(224)])
    # test_transforms = transforms.Compose([])

    val_dataset = Dataset(train_split, 'test', root, mode, test_transforms)
    val_dataloader = torch.utils.data.DataLoader(val_dataset, batch_size=1,
                                                 shuffle=False, num_workers=2,
                                                 pin_memory=False)

    dataloaders = {'test': val_dataloader}
    datasets = {'test': val_dataset}

    # setup the model
    if mode == 'flow':
        i3d = InceptionI3d(400, in_channels=2)
        i3d.load_state_dict(torch.load('weights/flow_imagenet.pt'))
    else:
        i3d = InceptionI3d(400, in_channels=3)
        i3d.load_state_dict(torch.load('weights/rgb_imagenet.pt'))
    i3d.replace_logits(num_classes)
    i3d.load_state_dict(torch.load(weights))  # nslt_2000_000700.pt nslt_1000_010800 nslt_300_005100.pt(best_results)  nslt_300_005500.pt(results_reported) nslt_2000_011400
    i3d.cuda()
    i3d = nn.DataParallel(i3d)
    i3d.eval()

    correct = 0
    correct_5 = 0
    correct_10 = 0
    # confusion_matrix = np.zeros((num_classes,num_classes), dtype=np.int)

    top1_fp = np.zeros(num_classes, dtype=np.int)
    top1_tp = np.zeros(num_classes, dtype=np.int)

    top5_fp = np.zeros(num_classes, dtype=np.int)
    top5_tp = np.zeros(num_classes, dtype=np.int)

    top10_fp = np.zeros(num_classes, dtype=np.int)
    top10_tp = np.zeros(num_classes, dtype=np.int)

    for data in dataloaders["test"]:
        inputs, labels, video_id = data  # inputs: b, c, t, h, w

        t = inputs.size(2)
        num = 64
        if t > num:
            num_segments = math.floor(t / num)

            segments = []
            for k in range(num_segments):
                segments.append(inputs[:, :, k*num: (k+1)*num, :, :])

            segments = torch.cat(segments, dim=0)
            per_frame_logits = i3d(segments)

            predictions = torch.mean(per_frame_logits, dim=2)

            if predictions.shape[0] > 1:
                predictions = torch.mean(predictions, dim=0)

        else:
            per_frame_logits = i3d(inputs)
            predictions = torch.mean(per_frame_logits, dim=2)[0]

        out_labels = np.argsort(predictions.cpu().detach().numpy())

        if labels[0].item() in out_labels[-5:]:
            correct_5 += 1
            top5_tp[labels[0].item()] += 1
        else:
            top5_fp[labels[0].item()] += 1
        if labels[0].item() in out_labels[-10:]:
            correct_10 += 1
            top10_tp[labels[0].item()] += 1
        else:
            top10_fp[labels[0].item()] += 1
        if torch.argmax(predictions).item() == labels[0].item():
            correct += 1
            top1_tp[labels[0].item()] += 1
        else:
            top1_fp[labels[0].item()] += 1
        print(video_id, float(correct) / len(dataloaders["test"]), float(correct_5) / len(dataloaders["test"]),
              float(correct_10) / len(dataloaders["test"]))

    top1_per_class = np.mean(top1_tp / (top1_tp + top1_fp))
    top5_per_class = np.mean(top5_tp / (top5_tp + top5_fp))
    top10_per_class = np.mean(top10_tp / (top10_tp + top10_fp))
    print('top-k average per class acc: {}, {}, {}'.format(top1_per_class, top5_per_class, top10_per_class))


def run_on_tensor(weights, ip_tensor, num_classes):
    i3d = InceptionI3d(400, in_channels=3)
    # i3d.load_state_dict(torch.load('models/rgb_imagenet.pt'))

    i3d.replace_logits(num_classes)
    i3d.load_state_dict(torch.load(weights))  # nslt_2000_000700.pt nslt_1000_010800 nslt_300_005100.pt(best_results)  nslt_300_005500.pt(results_reported) nslt_2000_011400
    i3d.cuda()
    i3d = nn.DataParallel(i3d)
    i3d.eval()

    t = ip_tensor.shape[2]
    ip_tensor.cuda()
    per_frame_logits = i3d(ip_tensor)

    predictions = F.upsample(per_frame_logits, t, mode='linear')

    predictions = predictions.transpose(2, 1)
    out_labels = np.argsort(predictions.cpu().detach().numpy()[0])

    arr = predictions.cpu().detach().numpy()[0,:,0].T

    plt.plot(range(len(arr)), F.softmax(torch.from_numpy(arr), dim=0).numpy())
    plt.show()

    return out_labels


def get_slide_windows(frames, window_size, stride=1):
    indices = torch.arange(0, frames.shape[0])
    window_indices = indices.unfold(0, window_size, stride)

    return frames[window_indices, :, :, :].transpose(1, 2)


if __name__ == '__main__':
    # ================== test i3d on a dataset ==============
    # need to add argparse

    # parser = argparse.ArgumentParser()
    # parser.add_argument('-mode', type=str,metavar = '',help='rgb or flow')
    # parser.add_argument('-save_model', type=str)
    # parser.add_argument('-root', type=str)

    # args = parser.parse_args()

    mode = 'rgb'
    num_classes = 2000
    
    ## Change to where the videos are located
    root = {'word':'videos'}

    train_split = 'preprocess/nslt_2000.json'
    weights = '/home/jovyan/work/WLASL_complete/checkpoints/nslt_2000_065846_0.447803.pt'

    run(mode=mode, root=root, train_split=train_split, weights=weights, datasets =datasets)
