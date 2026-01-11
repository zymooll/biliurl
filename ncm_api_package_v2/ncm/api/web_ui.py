"""
Web UI模块 - 提供HTML模板路径
分离后的web_ui模块，模板和静态资源已解耦
"""
import os

# 获取当前目录
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 模板目录路径
TEMPLATES_DIR = os.path.join(CURRENT_DIR, 'templates')

# 静态资源目录路径
STATIC_DIR = os.path.join(CURRENT_DIR, 'static')

# 模板文件路径
INDEX_TEMPLATE = os.path.join(TEMPLATES_DIR, 'index.html')
LOGIN_TEMPLATE = os.path.join(TEMPLATES_DIR, 'login.html')


def get_web_ui_html():
    """返回Web UI的HTML内容"""
    with open(INDEX_TEMPLATE, 'r', encoding='utf-8') as f:
        return f.read()


def get_login_page_html():
    """返回访问密码登录页面的HTML内容"""
    with open(LOGIN_TEMPLATE, 'r', encoding='utf-8') as f:
        return f.read()


# 保持向后兼容
def get_template_path(template_name):
    """获取模板文件路径"""
    return os.path.join(TEMPLATES_DIR, template_name)


def get_static_path(static_file):
    """获取静态资源文件路径"""
    return os.path.join(STATIC_DIR, static_file)
