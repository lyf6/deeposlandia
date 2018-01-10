#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
/**
 *   Raphael Delhome - december 2017
 *
 *   This library is free software; you can redistribute it and/or
 *   modify it under the terms of the GNU Library General Public
 *   License as published by the Free Software Foundation; either
 *   version 2 of the License, or (at your option) any later version.
 *   
 *   This library is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 *   Library General Public License for more details.
 *   You should have received a copy of the GNU Library General Public
 *   License along with this library; if not, see <http://www.gnu.org/licenses/>
 */
"""

from collections import defaultdict
from PIL import Image
import json
import math
import numpy as np
import os

import utils

class Dataset(object):

    def __init__(self, image_size, glossary_filename):
        """ Class constructor
        """
        self.image_size = image_size
        self.class_info = defaultdict()
        self.build_glossary(glossary_filename)
        self.image_info = defaultdict()

    def get_class(self, class_id):
        """ `class_info` getter, return only one class

        Parameters:
        -----------
        class_id: integer
            Id of the dataset class that must be returned
        """
        if not class_id in self.class_info.keys():
            print("Class {} not in the dataset glossary".format(class_id))
            return None
        return self.class_info[class_id]
    
    def get_image(self, image_id):
        """ `image_info` getter, return only the information for one image

        Parameters:
        -----------
        image_id: integer
            Id of the dataset image that must be returned
        """
        if not image_id in self.image_info.keys():
            print("Image {} not in the dataset".format(image_id))
            return None
        return self.image_info[image_id]

    def get_nb_class(self):
        """ `class_info` getter, return the size of `class_info`, i.e. the
        number of class in the dataset
        """
        return len(self.class_info)

    def get_nb_images(self):
        """ `image_info` getter, return the size of `image_info`, i.e. the
        number of images in the dataset
        """
        return len(self.image_info)

    def get_class_popularity(self):
        """
        """
        labels = [self.image_info[im]["labels"]
                  for im in self.image_info.keys()]
        if self.get_nb_images() == 0:
            utils.logger.info("No images in the dataset.")
            return None
        else:
            return np.round(np.divide(sum(np.array(labels)),
                                      self.get_nb_images()), 3)

    def build_glossary(self, config_filename):
        """Read the Mapillary glossary stored as a json file at the data
        repository root

        Parameter:
        ----------
        config_filename: object
            String designing the relative path of the dataset glossary
        (based on Mapillary dataset)
        """
        with open(config_filename) as config_file:
            glossary = json.load(config_file)
        if "labels" not in glossary.keys():
            print("There is no 'label' key in the provided glossary.")
            return None
        for lab_id, label in enumerate(glossary["labels"]):
            if label["evaluate"]:
                name_items = label["name"].split('--')
                category = '-'.join(name_items[:-1])
                self.add_class(lab_id, name_items[-1], label["color"], category)

    def add_class(self, class_id, class_name, color, category=None):
        """ Add a new class to the dataset with class id `class_id`

        Parameters:
        -----------
        class_id: integer
            Id of the new class
        class_name: object
            String designing the new class name
        color: list
            List of three integers (between 0 and 255) that characterizes the
        class (useful for semantic segmentation result printing)
        category: object
            String designing the category of the dataset class
        """
        if class_id in self.class_info.keys():
            print("Class {} already stored into the class set.".format(class_id))
            return None
        self.class_info[class_id] = {"name": class_name,
                                     "category": category,
                                     "color": color}

    def populate(self, datadir):
        """ Populate the dataset with images contained into `datadir` directory
 
       Parameter:
        ----------
        datadir: object
            String designing the relative path of the directory that contains
        new images
        """
        utils.make_dir(os.path.join(datadir, "input"))
        image_dir = os.path.join(datadir, "images")
        image_list = os.listdir(image_dir)
        image_list_longname = [os.path.join(image_dir, l) for l in image_list]
        for image_id, image_filename in enumerate(image_list_longname):
            label_filename = image_filename.replace("images/", "labels/")
            label_filename = label_filename.replace(".jpg", ".png")

            # open original images
            img_in = Image.open(image_filename)
            old_width, old_height = img_in.size
            img_out = Image.open(label_filename)

            # resize images (self.image_size*larger_size or larger_size*self.image_size)
            img_in = utils.resize_image(img_in, self.image_size)
            img_out = utils.resize_image(img_out, self.image_size)

            # crop images to get self.image_size*self.image_size dimensions
            crop_pix = np.random.randint(0, 1+max(img_in.size)-self.image_size)
            final_img_in = utils.mono_crop_image(img_in, crop_pix)
            final_img_out = utils.mono_crop_image(img_out, crop_pix)
            resizing_ratio = math.ceil(old_width * old_height
                                       / (self.image_size**2))

            # save final image
            new_filename = image_filename.replace("images/", "input/")
            final_img_in.save(new_filename)

            # label_filename vs label image
            labels = utils.mapillary_label_building(final_img_out,
                                                    self.get_nb_class())

            # add to dataset object
            self.add_image(image_id, image_filename, new_filename,
                           label_filename, labels)


    def add_image(self, image_id, raw_filename, image_filename,
                  label_filename, labels):
        """ Add a new image to the dataset with image id `image_id`; an image
                  in the dataset is represented by an id, an original filename,
                  a new version filename (the image is preprocessed), a label
                  filename for getting ground truth description and a list of
                  0-1 labels (1 if the i-th class is on the image, 0 otherwise)

        Parameters:
        -----------
        image_id: integer
            Id of the new image
        raw_filename: object
            String designing the new image original name on the file system
        image_filename: object
            String designing the new preprocessed image name on the file system
        label_filename: object
            String designing the new image ground-truth-version name on the
        file system
        labels: list
            List of 0-1 values, the i-th value being 1 if the i-th class is on
        the new image, 0 otherwise; the label list length correspond to the
        number of classes in the dataset
        """
        if image_id in self.image_info.keys():
            print("Image {} already stored into the class set.".format(image_id))
            return None
        self.image_info[image_id] = {"raw_filename": raw_filename,
                                     "image_filename": image_filename,
                                     "label_filename": label_filename,
                                     "labels": labels}

    def save(self, filename):
        """Save dataset in a json file indicated by `filename`

        Parameter
        ---------
        filename: object
            String designing the relative path where the dataset must be saved
        """
        with open(filename, 'w') as fp:
            json.dump({"image_size": self.image_size,
                       "classes": self.class_info,
                       "images": self.image_info},
                      fp)
        utils.logger.info("The dataset has been saved into {}".format(filename))

    def load(self, filename):
        """Load a dataset from a json file indicated by `filename`

        Parameter
        ---------
        filename: object
            String designing the relative path from where the dataset must be
        loaded
        """
        with open(filename) as fp:
            ds = json.load(fp)
            self.image_size = ds["image_size"]
            self.class_info = {int(k):ds["classes"][k] for k in ds["classes"].keys()}
            self.image_info = {int(k):ds["images"][k] for k in ds["images"].keys()}
        utils.logger.info("The dataset has been loaded from {}".format(filename))
