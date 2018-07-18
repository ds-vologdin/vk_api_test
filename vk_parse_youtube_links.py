import os
from datetime import datetime
import vk_api

# Используется для КЭШа
# Решение это плохое, глобальные переменные мешают чистоте функций.
# Надо об этом подумать.
users_id = {}


def fetch_history_conversations(tools, user_id):
    records = tools.get_all_iter(
        'messages.getHistory', 20,
        {'user_id': user_id, 'extended': 1, 'fields': 'last_name'}
    )
    return records


def fetch_user_name(vk, id):
    # TODO: надо подумать о кешировании, возможно словарь в глобальной области
    # видимости не лучший вариант
    if id in users_id:
        return users_id[id]
    try:
        user = vk.users.get(user_ids=id)
    except vk_api.exceptions.ApiError as e:
        print('vk_api (user_id {}): {}'.format(id, e))
        return
    users_id[id] = user[0]
    return user[0]


def find_youtube_links_in_attachment(vk, attachment):
    if attachment['type'] != 'video':
        return
    # Здесь важно использовать именно get(), поскольку ключ platform задан
    # не всегда. Подозреваю, что на свои видео vk platform не задаёт
    if attachment['video'].get('platform') != 'YouTube':
        return
    videos = vk.video.get(videos='{}_{}'.format(
        attachment['video']['owner_id'], attachment['video']['id']
    ))
    if len(videos['items']) == 0:
        return
    # В одном attachment только одно видео
    return videos['items'][0]['player']


def find_youtube_links_in_attachments(vk, attachments):
    if not attachments:
        return []
    links_attachment = []
    for attachment in attachments:
        link = find_youtube_links_in_attachment(vk, attachment)
        if link:
            links_attachment.append(link)
    return links_attachment


def is_links_youtube_in_message_body(message):
    return ('https://www.youtube.com/' in message['body'] or
            'https://youtu.be/' in message['body'])


def parse_messages_youtube_link(vk, messages):
    messages_with_youtube_link = []
    for number_message, message in enumerate(messages):
        from_id = message['from_id']
        user = fetch_user_name(vk, from_id)

        # Ссылки могут быть и в attachments
        links_attachment = find_youtube_links_in_attachments(
            vk, message.get('attachments')
        )

        if not (is_links_youtube_in_message_body(message) or links_attachment):
            continue

        read_state = 'read' if message['read_state'] == 1 else 'not read'

        messages_with_youtube_link.append({
            'user': user,
            'date_message': datetime.utcfromtimestamp(message['date']),
            'read_state': read_state,
            'message': message['body'],
            'links_attachment': links_attachment,
        })
    return messages_with_youtube_link


def get_username(user):
    if not user:
        return
    return '{} {}'.format(user['first_name'], user['last_name'])


def output_conversations_with_youtube_link(conversations):
    for conversation in conversations:
        print('='*80)
        print('Разговор с {}'.format(get_username(conversation['user'])))
        for message in conversation['messages']:
            print('{} {} ({}): {}'.format(
                get_username(message['user']), message['date_message'],
                message['read_state'], message['message']
            ))
            if not message['links_attachment']:
                continue
            print('links_attachment: {}'.format(
                ', '.join(message['links_attachment'])
            ))


def find_youtube_links_in_conversations(vk, vk_tools):
    conversations = vk_tools.get_all_iter(
        'messages.getConversations', 20, {'count': 20}
    )
    conversations_with_youtube_link = []
    for number, conversation in enumerate(conversations):
        user_id = conversation['conversation']['peer']['id']
        user_conversation = fetch_user_name(vk, user_id)
        messages = fetch_history_conversations(vk_tools, user_id)
        messages_youtube_link = parse_messages_youtube_link(vk, messages)
        if not messages_youtube_link:
            continue
        conversations_with_youtube_link.append({
            'user': user_conversation,
            'messages': messages_youtube_link,
        })
    return conversations_with_youtube_link


def main():
    login = os.environ.get('VK_LOGIN')
    passwd = os.environ.get('VK_PASSWD')

    vk_session = vk_api.VkApi(login, passwd)
    vk_session.auth()
    vk = vk_session.get_api()
    vk_tools = vk_api.VkTools(vk_session)

    print('''Сейчас скрипт может очень надолго задуматься.
Не переживайте, это нормально... Всё зависит от масштабов Вашей переписки''')
    conversations_with_youtube_link = find_youtube_links_in_conversations(
        vk, vk_tools
    )
    output_conversations_with_youtube_link(conversations_with_youtube_link)


if __name__ == '__main__':
    main()
