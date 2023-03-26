from concurrent.futures import ThreadPoolExecutor
import io
import requests
import telebot
from common import const
from common.log import logger
from channel.channel import Channel
from config import channel_conf_val, channel_conf
bot = telebot.TeleBot(token=channel_conf(const.TELEGRAM).get('bot_token'))
thread_pool = ThreadPoolExecutor(max_workers=8)

@bot.message_handler(commands=['help'])
def send_welcome(message):
    bot.send_message(message.chat.id, "<a>我是chatGPT机器人，开始和我聊天吧!</a>", parse_mode = "HTML")

# 处理文本类型消息
@bot.message_handler(content_types=['text'], chat_types=['private'])
def send_welcome(msg):
    # telegram消息处理
    TelegramChannel().handle(msg)

@bot.message_handler(content_types=['text'], chat_types=['group','supergroup','channel'])
def send_welcome(msg):
    # telegram群组消息处理
    TelegramChannel().handle_group(msg)

class TelegramChannel(Channel):
    def __init__(self):
        pass

    def startup(self):
        logger.info("开始启动[telegram]机器人")
        bot.infinity_polling()

    def handle(self, msg):
        logger.debug("[Telegram private] receive msg: " + msg.text)
        single_chat_users = channel_conf_val(const.TELEGRAM, 'single_chat_users')
        img_match_prefix = self.check_prefix(msg, channel_conf_val(const.TELEGRAM, 'image_create_prefix'))
        # 如果是图片请求
        if img_match_prefix:
            thread_pool.submit(self._do_send_img, msg, str(msg.chat.id))
        else:
            if (not single_chat_users or 'ALL_USERS' in single_chat_users or msg.from_user.username in single_chat_users):
                thread_pool.submit(self._dosend,msg.text,msg)

    def handle_group(self, msg):
        logger.debug("[Telegram group] receive msg: " + msg.text)
        img_match_prefix = self.check_prefix(msg, channel_conf_val(const.TELEGRAM, 'image_create_prefix'))
        
        group_chat_list = channel_conf_val(const.TELEGRAM, 'group_chat_list')
        match_prefix = self.check_prefix(msg, channel_conf_val(const.TELEGRAM, 'group_chat_prefix'))
        match_keyword = self.check_keyword(msg, channel_conf_val(const.TELEGRAM, 'group_chat_keyword'))
        # 如果是图片请求
        if img_match_prefix:
            thread_pool.submit(self._do_send_img, msg, str(msg.chat.id))
        else:
            if (not group_chat_list or 'ALL_GROUP' in group_chat_list or msg.chat.title in group_chat_list):
                if match_prefix or match_keyword:
                    if match_prefix != '':
                        str_list = msg.text.split(match_prefix, 1)
                        if len(str_list) == 2:
                            msg.text = str_list[1].strip()
                    thread_pool.submit(self._dosend,msg.text,msg)
        
    def _dosend(self,query,msg):
        context= dict()
        context['from_user_id'] = str(msg.chat.id)
        reply_text = super().build_reply_content(query, context)
        logger.info('[Telegram] reply content: {}'.format(reply_text))
        bot.reply_to(msg,reply_text)
        
    def _do_send_img(self, msg, reply_user_id):
        try:
            if not msg:
                return
            context = dict()
            context['type'] = 'IMAGE_CREATE'
            img_urls = super().build_reply_content(msg.text, context)
            if not img_urls:
                return
            if not isinstance(img_urls, list):
                bot.reply_to(msg,img_urls)
                return
            for url in img_urls:
            # 图片下载
                pic_res = requests.get(url, stream=True)
                image_storage = io.BytesIO()
                for block in pic_res.iter_content(1024):
                    image_storage.write(block)
                image_storage.seek(0)

                # 图片发送
                logger.info('[Telegrame] sendImage, receiver={}'.format(reply_user_id))
                bot.send_photo(msg.chat.id,image_storage)
        except Exception as e:
            logger.exception(e)

    def check_prefix(self, msg, prefix_list):
        if not prefix_list:
            return None
        for prefix in prefix_list:
            if msg.text.startswith(prefix):
                return prefix
        return None
    
    def check_keyword(self, msg, keyword_list):
        if not keyword_list:
            return True
        for keyword in keyword_list:
            if (msg.text.find(keyword) != -1):
                return True
        return False
    
    def check_contain(self, content, keyword_list):
        if not keyword_list:
            return None
        for ky in keyword_list:
            if content.find(ky) != -1:
                return True
        return None
