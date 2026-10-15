import os
import sys
import urllib.request
import vertexai
from vertexai import agent_engines
from google.cloud import aiplatform_v1

PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("REGION", "asia-northeast3")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET")
SWP_PROXY_URL = os.environ.get("SWP_PROXY_URL", "http://10.10.10.50:3128")

if not PROJECT_ID or not STAGING_BUCKET:
    print("오류: 실행 전 환경변수 PROJECT_ID와 STAGING_BUCKET을 먼저 설정해 주세요.")
    print("예시:")
    print('  export PROJECT_ID="your-gcp-project-id"')
    print('  export REGION="asia-northeast3"')
    print('  export STAGING_BUCKET="gs://your-staging-bucket"')
    sys.exit(1)

NETWORK_ATTACHMENT = (
    f"projects/{PROJECT_ID}/regions/{LOCATION}/networkAttachments/agent-nat-psc-attachment"
)

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)


class NatEgressTestAgent:
    def query(self, question: str = "check") -> dict:
        # HTTP 클라이언트에 SWP 사설 IP:포트(10.10.10.50:3128)를 프록시로 등록
        proxy_handler = urllib.request.ProxyHandler({
            "http": SWP_PROXY_URL,
            "https": SWP_PROXY_URL,
        })
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open("https://api.ipify.org?format=json", timeout=10) as response:
            ip_data = response.read().decode("utf-8").strip()
        return {
            "question": question,
            "swp_proxy_used": SWP_PROXY_URL,
            "detected_egress_public_ip": ip_data,
        }


if __name__ == "__main__":
    print(f"[1/2] PSC Interface({NETWORK_ATTACHMENT})를 연결하여 테스트 에이전트를 배포합니다...")
    remote_agent = agent_engines.create(
        agent_engine=NatEgressTestAgent(),
        display_name="agent-nat-swp-verify-agent",
        description="Agent Engine Egress Fixed IP Verification via SWP and Cloud NAT",
        requirements=[],
        psc_interface_config=aiplatform_v1.PscInterfaceConfig(
            network_attachment=NETWORK_ATTACHMENT
        ),
    )
    print(f"배포 완료 리소스명: {remote_agent.resource_name}")

    print("[2/2] 배포된 에이전트를 호출하여 외부 Egress 공인 IP를 확인합니다...")
    result = remote_agent.query(question="현재 에이전트가 외부로 나가는 공인 IP가 무엇인가요?")
    print("검증 결과:", result)
