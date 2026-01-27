#!/usr/bin/env python3
"""
Leaflow 多账号自动签到脚本
变量名：KATABUMP_ACCOUNTS
变量值：邮箱1:密码1
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import requests
from datetime import datetime
import random  # 新增，用于模拟随机行为

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LeaflowAutoCheckin:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        if not self.email or not self.password:
            raise ValueError("邮箱和密码不能为空")
        
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """设置Chrome驱动选项"""
        chrome_options = Options()
        
        # GitHub Actions环境配置
        if os.getenv('GITHUB_ACTIONS'):
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
        
        # 通用配置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        # 精准注入：抹除 webdriver 痕迹并实时清理翻译插件导致的 401 指纹
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                const observer = new MutationObserver(() => {
                    document.documentElement.removeAttribute('class');
                    document.documentElement.removeAttribute('translated-ltr');
                });
                observer.observe(document.documentElement, {attributes: true});
            """
        })
        
    def close_popup(self):
        """关闭初始弹窗"""
        try:
            logger.info("尝试关闭初始弹窗...")
            time.sleep(3)  # 等待弹窗加载
            
            # 尝试关闭弹窗
            try:
                actions = ActionChains(self.driver)
                actions.move_by_offset(10, 10).click().perform()
                logger.info("已成功关闭弹窗")
                time.sleep(2)
                return True
            except:
                pass
            return False
            
        except Exception as e:
            logger.warning(f"关闭弹窗时出错: {e}")
            return False
    
    def wait_for_element_clickable(self, by, value, timeout=10):
        """等待元素可点击"""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
    
    def wait_for_element_present(self, by, value, timeout=10):
        """等待元素出现"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    
    def login(self):
        """执行登录流程"""
        logger.info(f"开始登录流程")
        
        # 适配 KataBump 登录页面
        self.driver.get("https://dashboard.katabump.com/auth/login")
        time.sleep(5)
        
        # 关闭弹窗
        self.close_popup()
        
        # 输入邮箱
        try:
            logger.info("查找邮箱输入框...")
            time.sleep(2)
            
            email_selectors = [
                "input[name='email']",
                "input[type='email']",
                "input[type='text']",
                "input[placeholder*='邮箱']"
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = self.wait_for_element_clickable(By.CSS_SELECTOR, selector, 5)
                    logger.info(f"找到邮箱输入框")
                    break
                except:
                    continue
            
            if not email_input:
                raise Exception("找不到邮箱输入框")
            
            email_input.clear()
            email_input.send_keys(self.email)
            logger.info("邮箱输入完成")
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"输入邮箱时出错: {e}")
            try:
                self.driver.execute_script(f"document.querySelector('input[name=\"email\"]').value = '{self.email}';")
                logger.info("通过JavaScript设置邮箱")
                time.sleep(2)
            except:
                raise Exception(f"无法输入邮箱: {e}")
        
        # 等待密码输入框出现并输入密码
        try:
            logger.info("查找密码输入框...")
            password_input = self.wait_for_element_clickable(By.CSS_SELECTOR, "input[type='password']", 10)
            password_input.clear()
            password_input.send_keys(self.password)
            logger.info("密码输入完成")
            time.sleep(1)
        except:
            raise Exception("找不到密码输入框")
        
        # 点击登录按钮
        try:
            logger.info("查找登录按钮...")
            login_btn = self.wait_for_element_clickable(By.CSS_SELECTOR, "button[type='submit']", 5)
            login_btn.click()
            logger.info("已点击登录按钮")
        except Exception as e:
            raise Exception(f"点击登录按钮失败: {e}")
        
        # 等待登录完成
        try:
            WebDriverWait(self.driver, 20).until(
                lambda driver: "dashboard" in driver.current_url
            )
            logger.info(f"登录成功")
            return True
        except:
            raise Exception("登录跳转失败")
    
    def get_balance(self):
        """获取当前账号的总余额"""
        try:
            logger.info("获取账号余额...")
            self.driver.get("https://dashboard.katabump.com/dashboard")
            time.sleep(3)
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            import re
            numbers = re.findall(r'\d+\.?\d*', page_text)
            if numbers:
                return f"{numbers[0]}元"
            return "未知"
        except Exception as e:
            logger.warning(f"获取余额时出错: {e}")
            return "未知"
    
    def checkin(self):
        """执行续期流程 - 破解 401 拦截补丁"""
        logger.info("跳转到仪表板...")
        self.driver.get("https://dashboard.katabump.com/dashboard")
        time.sleep(5)
        
        # 1. 查找并点击 Renew 按钮
        try:
            renew_btn = self.wait_for_element_clickable(By.XPATH, "//button[contains(text(), 'Renew')]", 15)
            renew_btn.click()
            logger.info("已开启 Renew 弹窗，开始执行行为模拟...")
        except:
            raise Exception("找不到 Renew 按钮")

        # 2. 行为画像模拟：触发 selectionchange 监测
        try:
            actions = ActionChains(self.driver)
            actions.move_by_offset(random.randint(5, 20), random.randint(5, 20)).perform()
            time.sleep(1)
            # 随机双击一段文字，证明是“真人阅读”
            paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
            if paragraphs:
                actions.double_click(random.choice(paragraphs)).perform()
                logger.info("已触发行为画像监测 (selectionchange)")
        except:
            pass

        # 3. 核心补丁：强制静默等待 12 秒，确保 Cloudflare 验证完成
        logger.info("等待 12s 生成验证 Token (防止 401)...")
        time.sleep(12)
        
        # 4. 点击最终确认按钮
        try:
            final_btn = self.driver.find_element(By.CSS_SELECTOR, ".modal-footer .btn-primary")
            self.driver.execute_script("arguments[0].scrollIntoView();", final_btn)
            final_btn.click()
            logger.info("续期请求已提交")
            time.sleep(5)
            return "续期成功"
        except:
            raise Exception("无法点击最终确认按钮")
    
    def run(self):
        """单账号执行流程"""
        try:
            logger.info(f"开始处理账号")
            if self.login():
                result = self.checkin()
                balance = self.get_balance()
                logger.info(f"结果: {result}, 余额: {balance}")
                return True, result, balance
            else:
                raise Exception("登录失败")
        except Exception as e:
            error_msg = str(e)
            logger.error(error_msg)
            return False, error_msg, "未知"
        finally:
            if self.driver:
                self.driver.quit()

class MultiAccountManager:
    """多账号管理器 - 按照要求改为单账号读取"""
    def __init__(self):
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.accounts = self.load_accounts()
    
    def load_accounts(self):
        """仅加载单个账号配置 - 变量名已改为 KATABUMP_ACCOUNTS"""
        accounts = []
        # 直接读取 格式为 邮箱:密码 的字符串
        accounts_str = os.getenv('KATABUMP_ACCOUNTS', '').strip()
        if accounts_str and ':' in accounts_str:
            email, password = accounts_str.split(':', 1)
            accounts.append({'email': email.strip(), 'password': password.strip()})
            return accounts
        
        # 兼容旧单账号格式
        email = os.getenv('LEAFLOW_EMAIL', '').strip()
        password = os.getenv('LEAFLOW_PASSWORD', '').strip()
        if email and password:
            accounts.append({'email': email, 'password': password})
            return accounts
        
        raise ValueError("未找到有效账号配置")
    
    def send_notification(self, results):
        """发送汇总通知 - 保持原格式"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return
        try:
            email, success, result, balance = results[0]
            current_date = datetime.now().strftime("%Y/%m/%d")
            status = "✅" if success else "❌"
            message = f"🎁 KataBump自动续期通知\n📊 状态: {status}\n📅 签到时间：{current_date}\n\n账号：{email}\n{status} {result}！\n💰 当前总余额：{balance}。"
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            requests.post(url, data={"chat_id": self.telegram_chat_id, "text": message, "parse_mode": "HTML"})
        except Exception as e:
            logger.error(f"通知发送失败: {e}")
    
    def run_all(self):
        account = self.accounts[0]
        auto_checkin = LeaflowAutoCheckin(account['email'], account['password'])
        success, result, balance = auto_checkin.run()
        res_list = [(account['email'], success, result, balance)]
        self.send_notification(res_list)
        return success

def main():
    try:
        manager = MultiAccountManager()
        manager.run_all()
        exit(0)
    except Exception as e:
        logger.error(f"脚本执行出错: {e}")
        exit(1)

if __name__ == "__main__":
    main()
