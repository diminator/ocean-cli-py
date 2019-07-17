import os
from dropbox import Dropbox
import dropbox.sharing


def get_shared_folder_by_name(folder_name):
    dbx = Dropbox(os.getenv('DROPBOX_TOKEN', None))
    folder = [f for f in dbx.sharing_list_folders().entries
              if f.name == folder_name]
    return folder[0] if folder else None


def create_shared_folder(folder_name):
    dbx = Dropbox(os.getenv('DROPBOX_TOKEN', None))
    # metadata = dbx.files_create_folder(folder_name)
    return dbx.sharing_share_folder(folder_name)


def authorize_folder(emailAddress=None, folderId=None, folderName=None, *args, **kwargs):
    dbx = Dropbox(os.getenv('DROPBOX_TOKEN', None))
    if not folderId:
        folderId = get_shared_folder_by_name(folderName).shared_folder_id
    members = [dropbox.sharing.AddMember(
        dropbox.sharing.MemberSelector.email(emailAddress))
    ]
    return dbx.sharing_add_folder_member(folderId, members)
