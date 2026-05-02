import rclpy
from rclpy.node import Node
from autopatrol_interfaces.srv import SpeechText
import subprocess
import threading




class Speaker(Node):
    def __init__(self):
        super().__init__('speaker')
        self.speech_service = self.create_service(SpeechText,'speech_text',self.speech_text_callback)
        self.speech_lock = threading.Lock()

    def speech_text_callback(self,request,response):
        self.get_logger().info(f'正在准备朗读{request.text}')
        with self.speech_lock:
            self.speak(request.text)
        response.result = True
        return response

    def speak(self,text):
        subprocess.run(["espeak-ng", "-v", "zh", text])


def main():
    rclpy.init()
    node = Speaker()
    rclpy.spin(node)
    rclpy.shutdown()