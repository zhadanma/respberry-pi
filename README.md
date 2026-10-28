# 自适应多模态检测系统（crea3）

面向独居老人的特殊状况检测系统。检测**跌倒**、**非睡眠时段长时间静止**、**呼救声**与**异常声响**，
实时向家属推送警报，并支持 PC 端实时查看与回放异常片段。

完整需求、技术栈、架构与模块划分见 [项目需求与技术栈.md](项目需求与技术栈.md)，
阶段编排与排期见 [Proposal.md](Proposal.md)，两端接口基准见 [接口契约.md](接口契约.md)。

## 项目结构

```
crea3/
├── 项目需求与技术栈.md     # 需求、技术栈、架构、模块划分、开发顺序、风险
├── Proposal.md             # 三阶段编排、十周排期、里程碑与分工
├── 接口契约.md             # 冻结的字段级接口契约（v1）
├── monitor/                # 监控端（Python）—— 开发期跑在 PC，后期迁树莓派
└── pcapp/                  # PC 端应用（Java / Spring Boot）
```

## 开发环境

| 端 | 语言 | 环境 |
| --- | --- | --- |
| monitor | Python 3.12 | conda 环境 `crea3` |
| pcapp | Java 17 | IntelliJ IDEA（内置 Maven，无需单独安装） |

### 监控端

```bash
conda activate crea3
pip install -r monitor/requirements.txt
cp monitor/.env.example monitor/.env   # 首次使用；按需修改 PC_BASE_URL / API_TOKEN
python monitor/run.py
```

启动后：

- 摄像头画面以 MJPEG 发布在 `http://127.0.0.1:8000/stream/video`（需 `X-Auth-Token`）；
- 立即向 PC 上报一次状态报告，之后按配置周期上报；
- 每 10 秒拉取一次 PC 下发的配置。

发送一条演示警报（验证 `/api/alert` 链路）：

```bash
python monitor/run.py --send-alert
```

### PC 端

用 IntelliJ IDEA 打开 `pcapp/pom.xml`，等待依赖下载完成后运行 `PcAppApplication`；
或命令行：

```bash
cd pcapp && ./mvnw spring-boot:run
```

数据库：MySQL 8.0（本机服务 `MySQL80`）。首次使用先把
`pcapp/src/main/resources/application.properties.example` 复制成同目录下的
`application.properties`（该文件不入库），填好本机 MySQL 的账号密码
（也可用环境变量 `MYSQL_USERNAME` / `MYSQL_PASSWORD`），
库 `crea3` 会在首次启动时自动创建（连接串已带 `createDatabaseIfNotExist=true`）。

浏览器打开 `http://localhost:8080` —— 实时预览、告警、报告列表；`/settings.html` 改参数。
两端令牌必须一致：`monitor/.env` 的 `API_TOKEN` 与 `application.properties` 的 `app.api-token`。

## 开发阶段说明

开发前中期，监控端与 PC 端**都在 PC 上运行**；功能全部跑通后，再把监控端迁移到树莓派 5。

迁移时只需替换采集层实现（开发期 OpenCV 读 USB 摄像头 → 部署期 picamera2 读 CSI 摄像头），
上层逻辑不变。详见需求文档 §2.3、§6。
