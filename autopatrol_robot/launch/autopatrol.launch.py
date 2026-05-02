import launch
import launch_ros
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    urdf_package_path = get_package_share_directory('autopatrol_robot')
    default_patrol_config_path = os.path.join(urdf_package_path,'config','patrol_config.yaml')



    action_speaker = launch_ros.actions.Node(
        package='autopatrol_robot',
        executable='speaker',
        output = 'screen',
    )

    action_patrol_node = launch_ros.actions.Node(
        package='autopatrol_robot',
        executable='patrol_node',
        output = 'screen',
        parameters=[default_patrol_config_path]
    )

    return launch.LaunchDescription([
            action_speaker,
            action_patrol_node,
    ])