/** @file parameter_update.cpp
 *  @brief /esp_update サービスでESPにパラメータを単発送信するクライアント。
 */
#include "rclcpp/rclcpp.hpp"
#include "mirs_msgs/srv/parameter_update.hpp"  // 新しいサービスファイルをインクルード

#include <chrono>
#include <cstdlib>
#include <memory>

using namespace std::chrono_literals;

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);

    // ノードの作成
    auto node = rclcpp::Node::make_shared("parameter_update_client");

    // サービスクライアントの作成
    auto client = node->create_client<mirs_msgs::srv::ParameterUpdate>("esp_update");

    // YAMLファイルからパラメータを読み込むための宣言
    // 既定値は config.yaml と一致させること（単独起動時の安全側）
    node->declare_parameter("wheel_radius", 0.0391);
    node->declare_parameter("wheel_base", 0.39);
    node->declare_parameter("rkp", 40.0);
    node->declare_parameter("rki", 150.0);
    node->declare_parameter("rkd", 0.4);
    node->declare_parameter("lkp", 40.0);
    node->declare_parameter("lki", 150.0);
    node->declare_parameter("lkd", 0.4);

    // サービスが利用可能になるまで待機
    while (!client->wait_for_service(1s)) {
        if (!rclcpp::ok()) {
            RCLCPP_ERROR(node->get_logger(), "サービス待機中に中断されました。終了します。");
            return 1;
        }
        RCLCPP_INFO(node->get_logger(), "サービスが利用できません。再試行します...");
    }

    // リクエストの作成
    auto request = std::make_shared<mirs_msgs::srv::ParameterUpdate::Request>();

    // YAMLからパラメータを取得してリクエストに設定
    request->wheel_radius = node->get_parameter("wheel_radius").as_double();
    request->wheel_base = node->get_parameter("wheel_base").as_double();
    request->rkp = node->get_parameter("rkp").as_double();
    request->rki = node->get_parameter("rki").as_double();
    request->rkd = node->get_parameter("rkd").as_double();
    request->lkp = node->get_parameter("lkp").as_double();
    request->lki = node->get_parameter("lki").as_double();
    request->lkd = node->get_parameter("lkd").as_double();

    // サービスを呼び出す
    auto result = client->async_send_request(request);

    // 結果を待機
    if (rclcpp::spin_until_future_complete(node, result) == rclcpp::FutureReturnCode::SUCCESS) {
        const bool ok = result.get()->success;
        RCLCPP_INFO(node->get_logger(), "リクエストの成功状態: %s", ok ? "true" : "false");
        if (!ok) {
            rclcpp::shutdown();
            return 1;
        }
    } else {
        RCLCPP_ERROR(node->get_logger(), "サービス呼び出しに失敗しました。");
        rclcpp::shutdown();
        return 1;
    }

    rclcpp::shutdown();
    return 0;
}
