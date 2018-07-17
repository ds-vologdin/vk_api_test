import os
import datetime
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
    # TODO: надо подумать о кешировании
    if id in users_id:
        return users_id[id]

    user = vk.users.get(user_ids=id)
    if len(user) == 0:
        return
    users_id[id] = user[0]
    return user[0]


def main():
    login = os.environ.get('VK_LOGIN')
    passwd = os.environ.get('VK_PASSWD')

    vk_session = vk_api.VkApi(login, passwd)
    vk_session.auth()

    vk = vk_session.get_api()

    tools = vk_api.VkTools(vk_session)

    conversations = tools.get_all_iter(
        'messages.getConversations', 20, {'count': 20}
    )
    for number, conversation in enumerate(conversations):
        user_id = conversation['conversation']['peer']['id']
        user_conversation = fetch_user_name(vk, user_id)
        print('='*80)
        print('conversation with {} {}'.format(
            user_conversation['first_name'], user_conversation['last_name']
        ))
        messages = fetch_history_conversations(tools, user_id)
        for number_message, message in enumerate(messages):
            from_id = message['from_id']
            user = fetch_user_name(vk, from_id)
            date_message = datetime.datetime.utcfromtimestamp(message['date'])
            read_state = 'read' if message['read_state'] == 1 else 'not read'
            print('{} {} {} ({}): {}'.format(
                user['first_name'], user['last_name'], date_message,
                read_state, message['body']
            ))
            if number_message > 30:
                break
        if number > 2:
            break

if __name__ == '__main__':
    main()
