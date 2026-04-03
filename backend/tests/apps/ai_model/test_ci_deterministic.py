from langchain_core.messages import HumanMessage, SystemMessage

from apps.ai_model.ci_deterministic import build_deterministic_response


def test_build_deterministic_response_returns_sql_payload_for_known_case() -> None:
    response = build_deterministic_response(
        [
            SystemMessage(content="<SQL-Generation-Process>"),
            HumanMessage(content="最近订单总金额是多少？"),
        ]
    )

    assert '"success": true' in response
    assert "SELECT SUM(" in response
    assert '"chart-type": "table"' in response


def test_build_deterministic_response_returns_chart_payload_for_chart_stage() -> None:
    response = build_deterministic_response(
        [
            SystemMessage(content="chart stage"),
            HumanMessage(
                content="""<user-question>订单状态分别有多少条？</user-question>\n<chart-type>table</chart-type>"""
            ),
        ]
    )

    assert '"type": "table"' in response
    assert '"columns"' in response
