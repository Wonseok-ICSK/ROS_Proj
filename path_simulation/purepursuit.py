"""복구한 경로 추종 실험. 실행하면 가상 차량의 위치와 방향을 표시한다."""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.transforms import Affine2D


PATH = np.array([
    [2.00, 1.00], [1.25, 1.75], [5.25, 8.25],
    [7.25, 8.75], [11.75, 10.75], [12.00, 10.00],
])
SAMPLE_TIME = 0.1  # 시뮬레이션 한 스텝의 시간(초)
GOAL_RADIUS = 0.1
TRACK_WIDTH = 1.0


def derivative(pose, controls):
    """차체의 선속도와 각속도를 전역 좌표계의 (dx/dt, dy/dt, dθ/dt)로 바꾼다."""
    speed, angular_velocity = controls
    heading = pose[2]
    return np.array([speed * np.cos(heading), speed * np.sin(heading), angular_velocity])


class ControllerPurePursuit:
    def __init__(self, waypoints):
        self.waypoints = waypoints
        self.desired_linear_velocity = 0.6
        self.max_angular_velocity = 2.0
        self.lookahead_distance = 0.3

    def calc_goal_point(self, pose):
        # 복구본의 선택 규칙. 각 항은 차체 중심에서 해당 웨이포인트까지의 거리다.
        # 남은 거리 합이 크면 마지막 점을 선택해 중간 웨이포인트를 건너뛸 수 있다.
        distances = np.linalg.norm(self.waypoints - pose[:2], axis=1)
        closest = np.argmin(distances)
        remaining_distance = np.sum(distances) - np.sum(distances[:closest])
        for index in range(closest + 1, len(distances)):
            if remaining_distance <= self.lookahead_distance:
                return self.waypoints[index]
            remaining_distance -= distances[index]
        return self.waypoints[-1]

    def __call__(self, pose):
        dx, dy = self.calc_goal_point(pose) - pose[:2]
        heading_error = np.arctan2(dy, dx) - pose[2]
        speed = self.desired_linear_velocity
        omega = 2 * speed * np.sin(heading_error) / self.lookahead_distance
        return speed, np.clip(omega, -self.max_angular_velocity, self.max_angular_velocity)


def plot_transform(ax, pose, track_width, frame_size):
    x, y, heading = pose
    # 차체 중심에서 라디안 단위로 회전한 뒤 세계 좌표로 평행 이동한다.
    transform = Affine2D().rotate(heading).translate(x, y) + ax.transData
    ax.plot(x, y, "ro")
    ax.add_patch(plt.Rectangle(
        (-frame_size / 2, -track_width / 2), frame_size, track_width,
        edgecolor="k", facecolor="none", transform=transform,
    ))


def main():
    controller = ControllerPurePursuit(PATH)
    pose = np.array([*PATH[0], 0.0])
    fig, ax = plt.subplots()

    while np.linalg.norm(pose[:2] - PATH[-1]) > GOAL_RADIUS and plt.fignum_exists(fig.number):
        # 전진 오일러 적분. 화면 갱신 간격도 같은 초 단위를 사용한다.
        pose += derivative(pose, controller(pose)) * SAMPLE_TIME
        ax.clear()
        ax.plot(PATH[:, 0], PATH[:, 1], "k--d")
        plot_transform(ax, pose, TRACK_WIDTH, TRACK_WIDTH / 0.8)
        ax.set(xlim=(0, 13), ylim=(0, 13), aspect="equal")
        plt.pause(SAMPLE_TIME)

    plt.show()


if __name__ == "__main__":
    main()
