from geometry_msgs.msg import PoseStamped,Pose
from nav2_simple_commander.robot_navigator import BasicNavigator,TaskResult
import rclpy
from rclpy.node import Node
from tf2_ros import TransformListener, Buffer
from tf_transformations import euler_from_quaternion,quaternion_from_euler
from autopatrol_interfaces.srv import SpeechText
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
import cv2

class PatrolNode(BasicNavigator):
    def __init__(self, node_name='patrol_node'):
        super().__init__(node_name)
        self.declare_parameter('initial_point',[0.0, 0.0, 0.0])
        self.declare_parameter('target_points',[0.0, 0.0, 0.0, 1.0, 1.0, 1.57])
        self.declare_parameter('img_save_path','')
        self.initial_point_ = self.get_parameter('initial_point').value
        self.target_points_ = self.get_parameter('target_points').value
        self.img_save_path = self.get_parameter('img_save_path').value
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)
        self.speech_client = self.create_client(SpeechText,'speech_text')


        self.cv_bridge = CvBridge()
        self.latest_img = None
        self.img_sub = self.create_subscription(Image,'/camera_sensor/image_raw',self.img_callback,1)



    def img_callback(self,msg):
        self.latest_img = msg


    def record_img(self):
        if self.latest_img is not None:
            pose = self.get_current_pose()
            cv_image = self.cv_bridge.imgmsg_to_cv2(self.latest_img)
            cv2.imwrite(
                f'{self.img_save_path}img_{pose.translation.x:3.2f}_{pose.translation.y:3.2f}.png',
                cv_image
            )



    def get_pose_by_xyyaw(self, x, y, yaw):
        """
        返回PoseStamed对象(包含目标位置)
        """

        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.pose.position.x = x
        pose.pose.position.y = y


        quat = quaternion_from_euler(0,0,yaw)
        pose.pose.orientation.x = quat[0]
        pose.pose.orientation.y = quat[1]
        pose.pose.orientation.z = quat[2]
        pose.pose.orientation.w = quat[3]
        return pose

    def init_robrot_pose(self):
        """
        初始化机器人的位姿
        """
        self.initial_point_ = self.get_parameter('initial_point').value
        init_pose = self.get_pose_by_xyyaw(self.initial_point_[0],self.initial_point_[1],self.initial_point_[2])
        self.setInitialPose(init_pose)
        self.waitUntilNav2Active()



    def get_target_points(self):
        """
        通过target_points参数获取目标点的集合
        """
        points = []
        Xs = []
        Ys = []
        self.target_points_ = self.get_parameter('target_points').value
        for i in range(int(len(self.target_points_)/3)):
            x = self.target_points_[i*3]
            y = self.target_points_[i*3+1]
            yaw = self.target_points_[i*3+2]
            points.append(self.get_pose_by_xyyaw(x,y,yaw))
            Xs.append(x)
            Ys.append(y)
        return points,Xs,Ys

    def nav_to_pose(self,target_point):
        """
        导航到目标点
        """
        self.goToPose(target_point)
        while not self.isTaskComplete():
            feedback = self.getFeedback()
            self.get_logger().info(f'剩余距离{feedback.distance_remaining}')

        self.get_logger().info(f'导航结果{self.getResult()}')





    def get_current_pose(self):
        """
        获取机器人当前位置
        """
        while rclpy.ok():
            try:
                tf = self.buffer.lookup_transform('map', 'base_footprint', rclpy.time.Time(seconds=0), rclpy.time.Duration(seconds=1))
                transform = tf.transform
                self.get_logger().info(f'平移:{transform.translation}')
                return transform
            except Exception as e:
                self.get_logger().warn(f'不能够获取坐标变换，原因: {str(e)}')



    def send_request(self, text):
        # 创建请求
        while not self.speech_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'语音服务端未上线，等待服务端上线中。')


        request = SpeechText.Request()
        request.text = text
        future = self.speech_client.call_async(request)
        rclpy.spin_until_future_complete(self,future)
        if future.result() is not None:
            response = future.result()
            if response.result:
                self.get_logger().info(f'语音合成成功{text}')
            else:
                self.get_logger().warn(f'语音合成失败{text}')
        else:
            self.get_logger().warn(f'语音请求失败{text}')
    
                




def main():
    rclpy.init()
    patrol = PatrolNode()
    # rclpy.spin(patrol)
    patrol.send_request('正在准备初始化位置')
    patrol.init_robrot_pose()
    patrol.send_request('成功初始化位置')

    while rclpy.ok():
        points,Xs,Ys = patrol.get_target_points()

        for point,x,y in zip(points,Xs,Ys):
            patrol.send_request(f'正在准备前往{x},{y}')
            patrol.nav_to_pose(point)
            patrol.record_img()
            patrol.send_request(f'已到达{x},{y}')
    
        rclpy.shutdown()



