import pickle
import numpy as np
from PIL import Image
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
import random
from dataloader.split_train_test_video_2 import *    #Needed when running from spatial_cnn
# from split_train_test_video_2 import *        #Needed when running directly

from skimage import io, color, exposure

class spatial_dataset(Dataset):  
    def __init__(self, dic, root_dir, mode, transform=None):
 
        self.keys = list(dic.keys())
        self.values = list(dic.values())
        self.root_dir = root_dir
        self.mode =mode
        self.transform = transform

    def __len__(self):
        return len(self.keys)

    def load_ucf_image(self,video_name, index):
        path = self.root_dir + video_name+'/frame'
        indStr = str(index).zfill(4)

        img = Image.open(path +str(indStr)+'.jpg')
        transformed_img = self.transform(img)
        img.close()

        return transformed_img

    def __getitem__(self, idx):

        if self.mode == 'train':
            video_name, nb_clips = list(self.keys)[idx].split(' ')
            nb_clips = int(nb_clips)
            clips = []

            segments = 5
            for i in range(segments):
                clips.append(random.randint(int((nb_clips/segments) * i), int((nb_clips/segments) * (i+1) -1)))
            
        elif self.mode == 'val':
            video_name, index = list(self.keys)[idx].split(' ')
            index =abs(int(index))
        else:
            raise ValueError('There are only train and val mode')

        label = list(self.values)[idx]
        label = np.array(label).astype(np.float64)
        
        if self.mode=='train':
            data ={}
            for i in range(len(clips)):
                key = 'img'+str(i)
                index = clips[i]
                data[key] = self.load_ucf_image(video_name, index)
                    
            sample = (data, label)
        elif self.mode=='val':
            data = self.load_ucf_image(video_name,index)
            sample = (video_name, data, label)
        else:
            raise ValueError('There are only train and val mode')
           
        return sample

class spatial_dataloader():
    def __init__(self, BATCH_SIZE, num_workers, path, ucf_list, ucf_split):

        self.BATCH_SIZE=BATCH_SIZE
        self.num_workers=num_workers
        self.data_path=path
        self.frame_count ={}
        # split the training and testing videos
        splitter = UCF101_splitter(path=ucf_list,split=ucf_split)
        self.train_video, self.test_video = splitter.split_video()

    def load_frame_count(self):
        with open("../../bold_data/BOLD_ijcv/BOLD_public/annotations/framecount.pkl", "rb") as f:
        # with open("../bold_data/BOLD_ijcv/BOLD_public/annotations/framecount.pkl", "rb") as f:
            self.frame_count = pickle.load(f)

    def run(self):
        self.load_frame_count()
        self.get_training_dic()
        self.val_sample20()
        train_loader = self.train()
        val_loader = self.validate()

        return train_loader, val_loader, self.test_video

    def get_training_dic(self):
        #print '==> Generate frame numbers of each training video'
        self.dic_training={}
        for video in self.train_video:
            #print videoname
            # nb_frame = self.frame_count[video]-10+1
            nb_frame = self.frame_count[video]
            key = video+' '+ str(nb_frame)
            self.dic_training[key] = self.train_video[video]
                    
    def val_sample20(self):
        print('==> sampling testing frames')
        self.dic_testing={}
        for video in self.test_video:
            # nb_frame = self.frame_count[video]-10+1
            nb_frame = self.frame_count[video]-10+1
            interval = int(nb_frame/19)
            for i in range(19):
                frame = i*interval
                key = video+ ' '+str(frame)
                self.dic_testing[key] = self.test_video[video]      

    def train(self):
        training_set = spatial_dataset(dic=self.dic_training, root_dir=self.data_path, mode='train', transform = transforms.Compose([
                transforms.Resize([346,346]), ## Shape errors unless I do it this way
                transforms.RandomHorizontalFlip(),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225]) ##Do I need to change the normalization constants
                ]))
        print('==> Training data :',len(training_set),'frames')
        print(training_set[1][0]['img0'].size())

        train_loader = DataLoader(
            dataset=training_set, 
            batch_size=self.BATCH_SIZE,
            shuffle=True,
            num_workers=self.num_workers)
        return train_loader

    def validate(self):
        validation_set = spatial_dataset(dic=self.dic_testing, root_dir=self.data_path, mode='val', transform = transforms.Compose([
                transforms.Resize([346,346]), ## Shape errors unless I do it this way
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],std=[0.229, 0.224, 0.225])
                ]))
        
        print('==> Validation data :',len(validation_set),'frames')
        print(validation_set[1][1].size())

        val_loader = DataLoader(
            dataset=validation_set, 
            batch_size=self.BATCH_SIZE, 
            shuffle=False,
            num_workers=self.num_workers)
        return val_loader





if __name__ == '__main__':
    
    dataloader = spatial_dataloader(BATCH_SIZE=1, num_workers=1, 
                                path='../../bold_data/BOLD_ijcv/BOLD_public/frames/', 
                                ucf_list = '../../bold_data/BOLD_ijcv/BOLD_public/annotations/',
                                ucf_split = '04')
    train_loader,val_loader,test_video = dataloader.run()