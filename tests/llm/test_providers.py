from cryptogent.llm.contracts import LLMTaskName, ProviderRequest, TaskConstraints, TaskOptions
from cryptogent.llm.context import ContextManager
from cryptogent.llm.providers.openai_provider import OpenAIProvider


def test_openai_provider_json_mode_payload() -> None:
    captured = {}

    def fake_client(payload: dict) -> dict:
        captured.update(payload)
        return {"choices": [{"message": {"content": "{\"ok\":true}"}}]}

    ctx = ContextManager().build(task_name=LLMTaskName.NEWS_SUMMARY, raw_inputs={})
    req = ProviderRequest(
        task_name=LLMTaskName.NEWS_SUMMARY,
        prompt="{}",
        context=ctx,
        constraints=TaskConstraints(),
        options=TaskOptions(),
        system_message="sys",
        user_message="user",
        response_format="json",
    )
    provider = OpenAIProvider(model="gpt-test", client=fake_client, json_mode=True)
    resp = provider.generate(req)
    assert resp.content.strip() == "{\"ok\":true}"
    assert captured.get("response_format", {}).get("type") == "json_object"
