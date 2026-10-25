#include <algorithm>
#include <chrono>
#include <cmath>
#include <functional>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>

#include "geometry_msgs/msg/twist.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"

using namespace std::chrono_literals;

// /scan の近距離障害物でNav2の速度指令を遮断する最終ゲート。
class ScanSafetyGuard : public rclcpp::Node
{
public:
  ScanSafetyGuard()
  : Node("scan_safety_guard")
  {
    scan_topic_ = declare_parameter<std::string>("scan_topic", "/scan");
    input_topic_ = declare_parameter<std::string>("input_cmd_vel_topic", "/cmd_vel_nav");
    output_topic_ = declare_parameter<std::string>("output_cmd_vel_topic", "/cmd_vel");
    stop_distance_ = declare_parameter<double>("stop_distance", 0.35);
    resume_distance_ = declare_parameter<double>("resume_distance", 0.50);
    forward_angle_deg_ = declare_parameter<double>("forward_angle_deg", 30.0);
    scan_timeout_sec_ = declare_parameter<double>("scan_timeout_sec", 0.5);
    command_timeout_sec_ = declare_parameter<double>("command_timeout_sec", 0.5);

    if (!(std::isfinite(stop_distance_) && std::isfinite(resume_distance_) &&
      stop_distance_ > 0.0 && resume_distance_ > stop_distance_ &&
      forward_angle_deg_ > 0.0 && forward_angle_deg_ <= 180.0 &&
      scan_timeout_sec_ > 0.0 && command_timeout_sec_ > 0.0))
    {
      throw std::invalid_argument("invalid scan safety guard parameters");
    }

    auto qos = rclcpp::SensorDataQoS();
    scan_sub_ = create_subscription<sensor_msgs::msg::LaserScan>(
      scan_topic_, qos, std::bind(&ScanSafetyGuard::on_scan, this, std::placeholders::_1));
    cmd_sub_ = create_subscription<geometry_msgs::msg::Twist>(
      input_topic_, rclcpp::QoS(10),
      std::bind(&ScanSafetyGuard::on_command, this, std::placeholders::_1));
    cmd_pub_ = create_publisher<geometry_msgs::msg::Twist>(output_topic_, rclcpp::QoS(10));
    timer_ = create_wall_timer(50ms, std::bind(&ScanSafetyGuard::publish_command, this));

    RCLCPP_WARN(get_logger(),
      "Scan safety guard active: stop <= %.2fm, resume >= %.2fm, forward +/- %.1f deg; "
      "input %s -> output %s. No fresh scan means stopped.",
      stop_distance_, resume_distance_, forward_angle_deg_, input_topic_.c_str(),
      output_topic_.c_str());
  }

private:
  void on_scan(const sensor_msgs::msg::LaserScan::SharedPtr scan)
  {
    last_scan_ = std::chrono::steady_clock::now();
    have_scan_ = true;
    const double half_angle = forward_angle_deg_ * M_PI / 180.0;
    double min_range = std::numeric_limits<double>::infinity();
    std::size_t samples = 0;
    for (std::size_t i = 0; i < scan->ranges.size(); ++i) {
      const double angle = scan->angle_min + static_cast<double>(i) * scan->angle_increment;
      if (!std::isfinite(angle) || std::abs(std::remainder(angle, 2.0 * M_PI)) > half_angle) {
        continue;
      }
      const double range = scan->ranges[i];
      if (std::isnan(range) || range < scan->range_min) {
        continue;
      }
      ++samples;
      // +inf や range_max 超過は「検出物なし」として停止判定から除外する。
      if (std::isfinite(range) && range <= scan->range_max) {
        min_range = std::min(min_range, range);
      }
    }

    const bool should_stop = samples == 0 || min_range <= stop_distance_;
    const bool should_resume = samples > 0 && min_range >= resume_distance_;
    if (!stopped_ && should_stop) {
      stopped_ = true;
      RCLCPP_ERROR(get_logger(), "Obstacle/invalid forward scan: stopping robot");
    } else if (stopped_ && should_resume) {
      stopped_ = false;
      RCLCPP_WARN(get_logger(), "Forward clearance restored: releasing safety stop");
    }
  }

  void on_command(const geometry_msgs::msg::Twist::SharedPtr msg)
  {
    latest_command_ = *msg;
    have_command_ = true;
    last_command_ = std::chrono::steady_clock::now();
  }

  void publish_command()
  {
    const auto current_time = std::chrono::steady_clock::now();
    const bool scan_fresh = have_scan_ &&
      std::chrono::duration<double>(current_time - last_scan_).count() <= scan_timeout_sec_;
    const bool command_fresh = have_command_ &&
      std::chrono::duration<double>(current_time - last_command_).count() <= command_timeout_sec_;
    if (!scan_fresh && !stopped_) {
      stopped_ = true;
      RCLCPP_ERROR(get_logger(), "No fresh /scan: stopping robot");
    }
    if (!scan_fresh && have_scan_) {
      RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 2000, " /scan is stale; holding stop");
    }
    cmd_pub_->publish(scan_fresh && command_fresh && !stopped_ ?
      latest_command_ : geometry_msgs::msg::Twist{});
  }

  std::string scan_topic_, input_topic_, output_topic_;
  double stop_distance_{0.35}, resume_distance_{0.50}, forward_angle_deg_{30.0};
  double scan_timeout_sec_{0.5}, command_timeout_sec_{0.5};
  bool stopped_{false}, have_scan_{false}, have_command_{false};
  std::chrono::steady_clock::time_point last_scan_{};
  std::chrono::steady_clock::time_point last_command_{};
  geometry_msgs::msg::Twist latest_command_;
  rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ScanSafetyGuard>());
  rclcpp::shutdown();
  return 0;
}
