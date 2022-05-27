# coding: utf-8

import os


def get_im_list(filepath,ext):
    files_list=[]
    files = os.listdir(filepath)
    for fi in files:
        fi_d = os.path.join(filepath,fi)
        if os.path.isdir(fi_d):
            files_list += get_im_list(fi_d,ext)
        else:
            if fi_d.endswith(ext):
                files_list.append(os.path.join(filepath,fi))

    return  files_list
