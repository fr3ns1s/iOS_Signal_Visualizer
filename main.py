import os
import shutil
import sqlite3
import json
import avinit
from pathlib import Path
import NSKeyedUnArchiver
import sys
import webbrowser


base_path = ""
avatars_path = ""
container_path = ""
sqliteConnection = None
cursor = None
my_contact = None
contactsList = []
messageList = []
groupList = []


def get_my_contact():
    q = "select recipientUUID,recipientPhoneNumber from model_SignalRecipient where recipientUUID not in (select distinct (recipientUUID) from model_SignalAccount);"
    cursor.execute(q)
    user_recipient = cursor.fetchone()
    if user_recipient is not None:
        q = "select * from model_OWSUserProfile where recipientPhoneNumber == 'kLocalProfileUniqueId'"
        cursor.execute(q)
        row = cursor.fetchone()
        if row is not None:
            user = {'id': user_recipient['recipientUUID'], 'number': user_recipient['recipientPhoneNumber'],
                    'name': row['profileName'] + " " + row['familyName']
                    }
            if row['avatarFileName'] is not None:
                user['pic'] = container_path + "/ProfileAvatars/" + row['avatarFileName']
            else:
                user['pic'] = make_avatar_png("u_{}".format(row['Id']), user['name'])
            return user
    return None


def get_fullname_from_contact_blob(row):
    try:
        dict = NSKeyedUnArchiver.unserializeNSKeyedArchiver(row['contact'])
        fullname = dict['fullName']
    except sqlite3.Error as error:
        print("Error on parsing contact plist", error)
        return row['recipientPhoneNumber']
    return fullname


def make_avatar_png(filename, name):
    path = avatars_path.absolute().as_posix() + '/{}.png'.format(filename)
    avinit.get_png_avatar(name, output_file=path)
    return path


def get_contact_list():
    q = "select * from model_SignalRecipient LEFT JOIN model_SignalAccount ON model_SignalRecipient.recipientUUID = model_SignalAccount.recipientUUID " \
        "where model_SignalRecipient.recipientUUID != '{}'".format(my_contact['id'])
    cursor.execute(q)
    contacts = cursor.fetchall()
    for row in contacts:
        name = get_fullname_from_contact_blob(row)
        contact = {'id': row['recipientUUID'], 'number': row['recipientPhoneNumber'],
                   'name': name, 'pic': make_avatar_png("c_{}".format(row['Id']), name)}
        contactsList.append(contact)


def get_group_members(uniqueId):
    q = "select * from model_TSGroupMember where groupThreadId == '{}'".format(uniqueId)
    cursor.execute(q)
    members = cursor.fetchall()
    group_members = []
    for member in members:
        group_members.append(member['uuidString'])
    return group_members


def get_group_image(group, name):
    try:
        dict = NSKeyedUnArchiver.unserializeNSKeyedArchiver(group['groupModel'])
        if 'avatarHash' in dict.keys():
            image = dict['avatarHash'] + ".png"
            image = container_path + "/GroupAvatars/" + image
        else:
            image = make_avatar_png("g_{}".format(group['Id']), name)
    except sqlite3.Error as error:
        print("Error on parsing contact plist", error)
        return ""
    return image


def get_groupname(group):
    try:
        dict = NSKeyedUnArchiver.unserializeNSKeyedArchiver(group['groupModel'])
        name = dict["groupName"]
    except sqlite3.Error as error:
        print("Error on parsing contact plist", error)
        return ""
    return name


def get_call_detail(InteractionRowId, threadRowId):
    try:
        q = "select * from CallRecord where InteractionRowId == '{}' and threadRowId == '{}'".format(InteractionRowId,
                                                                                                     threadRowId)
        cursor.execute(q)
        call_info = cursor.fetchone()
        call_body = ""
        if call_info is not None and call_info['type'] != 2:
            call_body += "📞 Call " if call_info['type'] == 0 else "🎥 Videoclcall "
            call_body += "incoming - " if call_info['direction'] == 0 else "outcoming - "
        else:
            call_body = "🎥 Group videocall terminated"
        return call_body
    except sqlite3.Error as error:
        print("Error on parsing call detail", error)
        return None


def get_attachment_detail(row):
    try:
        q = ""
        arr_att = NSKeyedUnArchiver.unserializeNSKeyedArchiver(row['attachmentIds'])
        if len(arr_att) > 1:
            q = "select * from model_TSAttachment where uniqueId IN {}".format(tuple(arr_att))
        elif len(arr_att)  == 1:
            q = "select * from model_TSAttachment where uniqueId = '{}'".format(arr_att[0])
        elif len(arr_att) == 0 and row['messageSticker'] is not None:
            arr_att = NSKeyedUnArchiver.unserializeNSKeyedArchiver(row['messageSticker'])
            q = "select * from model_TSAttachment where uniqueId = '{}'".format(arr_att['attachmentId'])
        cursor.execute(q)
        attachments = cursor.fetchall()
        res = []
        for attachment in attachments:
                file_path = container_path + "/Attachments" + attachment['localRelativeFilePath']
                res.append({'contentType': attachment['contentType'], 'path': file_path})
        return res
    except sqlite3.Error as error:
        print("Error on parsing attachment detail", error)
        return []


def get_group_list_and_messages():
    q = "select * from model_TSThread where uniqueId != '00000000-0000-0000-0000-000000000000' AND lastInteractionRowId != 0  AND groupModel != '' order by creationDate DESC"
    cursor.execute(q)
    groups = cursor.fetchall()
    for row in groups:
        name = get_groupname(row)
        group = {'id': row['uniqueId'], 'name': name,
                 'pic': get_group_image(row, name),
                 'members': get_group_members(row['uniqueId'])}
        groupList.append(group)
        get_message_list_group(row['uniqueId'])


def make_message_dict(row, thid, isGroup, contactUUID):
    dict = {}
    attachments = []
    dict['type'] = 'Text'
    dict['body'] = row['body'] if row['body'] is not None else ""
    if row['attachmentIds'] is not None or row['messageSticker'] is not None:
        attachments = get_attachment_detail(row)
    else:
        call = get_call_detail(row['Id'], thid)
        if call is not None:
            dict['body'] = call
            dict['type'] = 'Call'

    recvId = thid
    if isGroup == False:
        recvId = contactUUID if row['authorUUID'] is None else my_contact['id']

    message = {'id': row['uniqueId'],
               'sender': row['authorUUID'] if row['authorUUID'] is not None else my_contact['id'],
               'recvId': recvId,
               'status': 2 if row['read'] == 1 else 1, 'time': row['timestamp'], 'recvIsGroup': isGroup}

    for key in dict.keys():
        message[key] = dict[key]

    if len(attachments) == 0:
        if message['body'] == "" and message['type'] == "Text":
            return
        else:
            messageList.append(message)
    else:
        for attachment in attachments:
            message['type'] = 'Attachment'
            message.update(attachment)
            if message['body'] == "" and message['type'] == "Text":
                continue
            messageList.append(message)


def get_message_list_group(groupId):
    sqlite_select_Query = "select * from model_TSInteraction where uniqueThreadId == '{}' order by timestamp DESC".format(
        groupId)
    cursor.execute(sqlite_select_Query)
    messages = cursor.fetchall()
    for row in messages:
        make_message_dict(row, groupId, True, None)


def get_message_list_chat():
    q = "select * from model_TSThread where uniqueId != '00000000-0000-0000-0000-000000000000' " \
        "AND contactUUID != '' AND lastInteractionRowId != 0 order by creationDate DESC"
    cursor.execute(q)
    chats = cursor.fetchall()
    for row_chat in chats:
        q = "select * from model_TSInteraction where uniqueThreadId == '{}' order by timestamp DESC".format(
            row_chat['uniqueId'])
        cursor.execute(q)
        messages = cursor.fetchall()
        for row in messages:
            make_message_dict(row, row_chat['Id'], False, row_chat['contactUUID'])


def main(db_path, group_path):
    try:
        global base_path
        base_path = os.getcwd()
        global avatars_path
        avatars_path = Path(base_path + '/site/avatars/')
        if avatars_path.exists() and avatars_path.is_dir():
            shutil.rmtree(avatars_path)
        os.mkdir(avatars_path.absolute().as_posix())
        global container_path
        container_path = group_path
        global sqliteConnection
        sqliteConnection = sqlite3.connect(db_path)
        sqliteConnection.row_factory = sqlite3.Row
        global cursor
        cursor = sqliteConnection.cursor()
        print("Successfully Connected to SQLite")
        global my_contact
        my_contact = get_my_contact()
        if my_contact is None:
            print("Personal contact not found! Exiting...")
            exit(0)
        with open(base_path + "/site/datastore.js", "w") as outfile:
            contactsList.append(my_contact)
            outfile.write("let user = JSON.parse('" + json.dumps(my_contact).replace('\n', '') + "')\n")
            get_contact_list()
            outfile.write("let contactList = JSON.parse('" + json.dumps(contactsList).replace('\n', '') + "')\n")
            get_group_list_and_messages()
            get_message_list_chat()
            outfile.write("let groupList = JSON.parse('" + json.dumps(groupList).replace('\n', '') + "')\n")
            outfile.write("let messages = JSON.parse('" + json.dumps(messageList).replace('\n', '') + "')\n")
        outfile.close()
        print("Contacts: {}".format(len(contactsList)))
        print("Groups: {}".format(len(groupList)))
        print("Messages: {}".format(len(messageList)))
        webbrowser.open("file://{}/site/index.html".format(base_path))
    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if sqliteConnection:
            sqliteConnection.close()
            print("The SQLite connection is closed")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Command: main.py path_signal_decrypted.db path_signal_appgroup_folder")
    else:
        main(sys.argv[1], sys.argv[2])
