/** @file parameter_publisher.cpp
 *  @brief /params でESP用パラメータ（車輪・PID）を定期転送するノード。
 */
#include "rclcpp/rclcpp.hpp"
#include "mirs_msgs/msg/basic_param.hpp"
#include <chrono>
#include <memory>

/** @brief パラメータ転送ノード。config.yaml値をPUBLISH_PERIOD_MS毎に配信する。 */
class ParameterPublisher : public rclcpp::Node
{
    static constexpr int PUBLISH_PERIOD_MS = 500;  // ESP用パラメータ転送周期（2Hz）

public:
    ParameterPublisher()
        : Node("parameter_publisher")
    {
        // パラメータを宣言
        this->declare_parameter("wheel_radius", 0.04);
        this->declare_parameter("wheel_base", 0.38);
        this->declare_parameter("rkp", 40.0);
        this->declare_parameter("rki", 150.0);
        this->declare_parameter("rkd", 0.4);
        this->declare_parameter("lkp", 40.0);
        this->declare_parameter("lki", 150.0);
        this->declare_parameter("lkd", 0.4);

        // YAMLファイルからパラメータを取得
        wheel_radius = this->get_parameter("wheel_radius").as_double();
        wheel_base = this->get_parameter("wheel_base").as_double();
        rkp = this->get_parameter("rkp").as_double();
        rki = this->get_parameter("rki").as_double();
        rkd = this->get_parameter("rkd").as_double();
        lkp = this->get_parameter("lkp").as_double();
        lki = this->get_parameter("lki").as_double();
        lkd = this->get_parameter("lkd").as_double();

        // パブリッシャーの作成
        param_pub_ = this->create_publisher<mirs_msgs::msg::BasicParam>("/params", 10);

        // タイマーで定期的にオドメトリをパブリッシュ
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(PUBLISH_PERIOD_MS), std::bind(&ParameterPublisher::publish_parameter, this));
    }

private:
    void publish_parameter()
    {
        auto param_msg = mirs_msgs::msg::BasicParam();
        param_msg.wheel_base = wheel_base;
        param_msg.wheel_radius = wheel_radius;
        param_msg.rkp = rkp;
        param_msg.rki = rki;
        param_msg.rkd = rkd;
        param_msg.lkp = lkp;
        param_msg.lki = lki;
        param_msg.lkd = lkd;
        param_pub_->publish(param_msg);
    }

    // パブリッシャー
    rclcpp::Publisher<mirs_msgs::msg::BasicParam>::SharedPtr param_pub_;

    // タイマー
    rclcpp::TimerBase::SharedPtr timer_;

    // エンコーダの変数
    double wheel_radius,wheel_base,rkp,rki,rkd,lkp,lki,lkd;
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ParameterPublisher>());
    rclcpp::shutdown();
    return 0;
}
