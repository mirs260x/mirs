// Copyright 2026 mirs260x
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
// THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.


/** @file basic_command.cpp
 *  @brief /esp_cmd サービスで汎用コマンド（param1〜4）を単発送信するクライアント。
 */
#include <chrono>
#include <cstdlib>
#include <memory>

#include "rclcpp/rclcpp.hpp"
#include "mirs_msgs/srv/basic_command.hpp"  // 新しいサービスファイルをインクルード

using namespace std::chrono_literals;

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);

  auto node = rclcpp::Node::make_shared("basic_command_client");

  auto client = node->create_client<mirs_msgs::srv::BasicCommand>("esp_cmd");

    // 左はyamlから取る値、右はデフォルト値
  node->declare_parameter("param1", 1.0);
  node->declare_parameter("param2", 0.0);
  node->declare_parameter("param3", 0.0);
  node->declare_parameter("param4", 0.0);

    // サービスが利用可能になるまで待機
  while (!client->wait_for_service(1s)) {
    if (!rclcpp::ok()) {
      RCLCPP_ERROR(node->get_logger(), "Interrupted while waiting for the service. Exiting.");
      return 1;
    }
    RCLCPP_INFO(node->get_logger(), "service not available, waiting again...");
  }

    // リクエストの作成
  auto request = std::make_shared<mirs_msgs::srv::BasicCommand::Request>();

  request->param1 = node->get_parameter("param1").as_double();
  request->param2 = node->get_parameter("param2").as_double();
  request->param3 = node->get_parameter("param3").as_double();
  request->param4 = node->get_parameter("param4").as_double();

  auto result = client->async_send_request(request);

  if (rclcpp::spin_until_future_complete(node, result) == rclcpp::FutureReturnCode::SUCCESS) {
    const bool ok = result.get()->success;
    RCLCPP_INFO(node->get_logger(), "リクエストの成功状態: %s", ok ? "true" : "false");
    rclcpp::shutdown();
    return ok ? 0 : 1;
  } else {
    RCLCPP_ERROR(node->get_logger(), "サービス呼び出しに失敗しました。");
    rclcpp::shutdown();
    return 1;
  }
}
