/** @file encoder_reset.cpp
 *  @brief /reset_encoder サービスでESPのエンコーダをリセットするクライアント。
 */
#include "rclcpp/rclcpp.hpp"
#include "mirs_msgs/srv/simple_command.hpp"

#include <chrono>
#include <cstdlib>
#include <memory>

using namespace std::chrono_literals;

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);

  auto node = rclcpp::Node::make_shared("encoder_reset");
  auto client = node->create_client<mirs_msgs::srv::SimpleCommand>("reset_encoder");
  auto request = std::make_shared<mirs_msgs::srv::SimpleCommand::Request>();

  while (!client->wait_for_service(1s)) {
    if (!rclcpp::ok()) {
      RCLCPP_ERROR(node->get_logger(), "Interrupted while waiting for the service. Exiting.");
      return 1;
    }
    RCLCPP_INFO(node->get_logger(), "service not available, waiting again...");
  }

  auto result = client->async_send_request(request);
  // Wait for the result.
  if (rclcpp::spin_until_future_complete(node, result) ==
    rclcpp::FutureReturnCode::SUCCESS)
  {
    const bool ok = result.get()->success;
    RCLCPP_INFO(node->get_logger(), "Success: %s", ok ? "true" : "false");
    rclcpp::shutdown();
    return ok ? 0 : 1;
  } else {
    RCLCPP_ERROR(node->get_logger(), "Failed to call service");
    rclcpp::shutdown();
    return 1;
  }
}
