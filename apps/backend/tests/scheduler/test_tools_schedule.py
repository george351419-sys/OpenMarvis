from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from openmarvis.scheduler.tools_schedule import (
    CancelScheduleTool,
    CreateScheduleTool,
    ListSchedulesTool,
)


def _ctx(mgr):
    ctx = MagicMock()
    ctx.user_settings = MagicMock()
    ctx.user_settings.scheduler_manager = mgr
    ctx.security = MagicMock()
    cred = MagicMock()
    cred.mask.side_effect = lambda s: s          # default: no masking
    ctx.security.credential_guard = cred
    return ctx


@pytest.mark.asyncio
async def test_create_schedule_once_ok():
    mgr = MagicMock()
    mgr.add_once.return_value = "sch_x"
    tool = CreateScheduleTool()
    args = tool.args_model(trigger_type="once",
                            trigger_spec="2099-01-01T00:00:00+00:00",
                            instruction="hi", description="d",
                            origin_conv_id="conv1")
    res = await tool.execute(args, _ctx(mgr))
    assert res.error is None
    mgr.add_once.assert_called_once()
    payload = res.cards[0].payload
    assert "sch_x" in payload


@pytest.mark.asyncio
async def test_create_schedule_masks_credential():
    mgr = MagicMock()
    mgr.add_once.return_value = "sch_y"
    ctx = _ctx(mgr)
    ctx.security.credential_guard.mask.side_effect = \
        lambda s: s.replace("sk-ABCDE", "sk-***")

    tool = CreateScheduleTool()
    args = tool.args_model(trigger_type="once",
                            trigger_spec="2099-01-01T00:00:00+00:00",
                            instruction="run with sk-ABCDE",
                            description="d", origin_conv_id="c")
    res = await tool.execute(args, ctx)
    assert res.error is None
    forwarded = mgr.add_once.call_args.kwargs["instruction"]
    assert "sk-***" in forwarded
    assert "sk-ABCDE" not in forwarded


@pytest.mark.asyncio
async def test_create_schedule_rejects_bad_iso_for_once():
    mgr = MagicMock()
    tool = CreateScheduleTool()
    args = tool.args_model(trigger_type="once",
                            trigger_spec="not iso",
                            instruction="x", description="",
                            origin_conv_id="c")
    res = await tool.execute(args, _ctx(mgr))
    assert res.error is not None
    assert "trigger_spec" in res.error


@pytest.mark.asyncio
async def test_list_returns_rows():
    from openmarvis.scheduler.manager import ScheduleRow
    mgr = MagicMock()
    mgr.list.return_value = [
        ScheduleRow(id="sch_1", origin_conv_id="c1", trigger_type="once",
                     trigger_spec="...", instruction="hi", description="d",
                     next_run_at=None),
    ]
    tool = ListSchedulesTool()
    res = await tool.execute(tool.args_model(), _ctx(mgr))
    assert "sch_1" in res.content


@pytest.mark.asyncio
async def test_cancel_schedule_ok():
    mgr = MagicMock()
    mgr.cancel.return_value = True
    tool = CancelScheduleTool()
    res = await tool.execute(tool.args_model(schedule_id="sch_1"), _ctx(mgr))
    assert res.error is None
    mgr.cancel.assert_called_once_with("sch_1")


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_desc", [
    "每天 9 点晨会",
    "明天备份",
    "30 分钟后提醒",
    "9:00 喝水",
    "Every day backup",
    "2026-06-10 备份",
])
async def test_create_schedule_rejects_time_word_in_description(bad_desc: str):
    mgr = MagicMock()
    tool = CreateScheduleTool()
    args = tool.args_model(trigger_type="once",
                            trigger_spec="2099-01-01T00:00:00+00:00",
                            instruction="x", description=bad_desc,
                            origin_conv_id="c")
    res = await tool.execute(args, _ctx(mgr))
    assert res.error is not None
    assert "title_contains_time_word" in res.error
    # 真正没调到 manager —— 校验在 manager 之前
    mgr.add_once.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("clean_desc", [
    "晨会提醒",
    "备份重要文档",
    "alert important",
    "",  # 允许空 description
])
async def test_create_schedule_accepts_clean_description(clean_desc: str):
    mgr = MagicMock()
    mgr.add_once.return_value = "sch_ok"
    tool = CreateScheduleTool()
    args = tool.args_model(trigger_type="once",
                            trigger_spec="2099-01-01T00:00:00+00:00",
                            instruction="x", description=clean_desc,
                            origin_conv_id="c")
    res = await tool.execute(args, _ctx(mgr))
    assert res.error is None
    mgr.add_once.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_returns_error_when_missing():
    mgr = MagicMock()
    mgr.cancel.return_value = False
    tool = CancelScheduleTool()
    res = await tool.execute(tool.args_model(schedule_id="sch_xyz"), _ctx(mgr))
    assert res.error is not None
