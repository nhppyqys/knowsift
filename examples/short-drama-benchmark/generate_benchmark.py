#!/usr/bin/env python3
"""Generate the certificate-backed short-drama benchmark from captured sources."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


CASE_DIR = Path(__file__).resolve().parent
SKILL_ROOT = CASE_DIR.parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from knowledge_compiler import compile_claim  # noqa: E402
from knowledge_compiler.knowledge_document import (  # noqa: E402
    render_knowledge_document,
    validate_source_bundle,
)


def anchor(text: str, fragment: str) -> Dict[str, Any]:
    start = text.index(fragment)
    return {"text": fragment, "start": start, "end": start + len(fragment)}


def ir(
    claim_id: str,
    text: str,
    operator: str,
    subject: str,
    predicate: str,
    object_: str,
) -> Dict[str, Any]:
    return {
        "claim_id": claim_id,
        "source_text": text,
        "operator": operator,
        "subject": subject,
        "predicate": predicate,
        "object": object_,
        "polarity": "POSITIVE",
        "quantifier": "UNSPECIFIED",
        "modality": "ASSERTED",
        "scope": {},
        "anchors": {
            "subject": anchor(text, subject),
            "predicate": anchor(text, predicate),
            "object": anchor(text, object_),
        },
    }


def evidence(
    evidence_id: str,
    source_id: str,
    source_kind: str,
    source_text: str,
    fragment: str,
) -> Dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "source_kind": source_kind,
        "source_text": source_text,
        "quote": anchor(source_text, fragment),
        "derived_from": [],
        "cites": [],
    }


def single_evidence_claim(
    *,
    claim_id: str,
    text: str,
    operator: str,
    subject: str,
    predicate: str,
    object_: str,
    source_id: str,
    source_kind: str,
    source_text: str,
    evidence_fragment: str,
    relation: str = "ENTAILS",
    missing_bridge: str = "",
) -> Dict[str, Any]:
    claim_fragment = text.rstrip("。")
    evidence_id = f"E-{claim_id}"
    return {
        "claim_ir": ir(claim_id, text, operator, subject, predicate, object_),
        "evidence": [
            evidence(
                evidence_id,
                source_id,
                source_kind,
                source_text,
                evidence_fragment,
            )
        ],
        "semantic_reviews": [
            {
                "claim_id": claim_id,
                "evidence_id": evidence_id,
                "relation": relation,
                "claim_fragment": claim_fragment,
                "evidence_fragment": evidence_fragment,
                "missing_bridge": missing_bridge,
            }
        ],
    }


def build_source_bundle() -> Dict[str, Any]:
    return {
        "bundle_version": "1.0",
        "topic": "个人或小团队如何制作网络短剧并建立可验证的收入路径",
        "question": "B站和YouTube上的短剧教程中，哪些是可复用知识，哪些只是经验、营销承诺或待验证假设？",
        "language": "zh-CN",
        "source_boundary": (
            "检索日为2026-08-21。包含5个B站创作者页面、1个YouTube创作者视频、"
            "YouTube与B站官方规则、国家广电总局文件、StudioBinder制作指南及"
            "DramaBox日本创作者页面。网页内容按短摘录或结构化事实捕获；没有获得"
            "完整视频字幕的内容只用于确认标题、简介或发布者主张。"
        ),
        "sources": [
            {
                "source_id": "GUIDE-STUDIOBINDER-2025",
                "title": "Making a Short Film — Pre Production Workflow Step-by-Step",
                "source_type": "AUTHORITATIVE_GUIDANCE",
                "medium": "ARTICLE",
                "locator": "https://www.studiobinder.com/blog/making-short-film-pre-production/",
                "published_at": "2025-04-05",
                "captured_at": "2026-08-21",
                "content": (
                    "The Screenplay; The Schedule; The Budget.\n"
                    "Breaking down the script; Shot listing and/or storyboarding; Scheduling production; "
                    "Hiring cast and crew; Securing shoot locations."
                ),
                "notes": "短摘录，用于核对前期制作基础文件与任务。",
            },
            {
                "source_id": "YT-D4DARIOUS-TIPS",
                "title": "How to Make A Short Film: Important Tips and Advice",
                "source_type": "EXPERT_INTERPRETATION",
                "medium": "VIDEO",
                "locator": "https://www.youtube.com/watch?v=PalEaciHvXI",
                "published_at": "2014-01-20",
                "captured_at": "2026-08-21",
                "content": "The description says the video covers managing backstory and what to avoid in the writing process.",
                "notes": "仅捕获YouTube页面简介，没有把整段视频当作已转录证据。",
            },
            {
                "source_id": "BILI-STORYBOARD",
                "title": "拍摄视频第一步：了解视频创作与分镜脚本设计",
                "source_type": "EXPERT_INTERPRETATION",
                "medium": "ARTICLE",
                "locator": "https://www.bilibili.com/opus/602498179786822057",
                "published_at": "2021-12-01",
                "captured_at": "2026-08-21",
                "content": "拍摄脚本一般包含画面内容、镜头运动、景别、长度、台词、音乐音效、转场方式和道具。",
                "notes": "B站创作者文章摘录。",
            },
            {
                "source_id": "BILI-AI-COURSE",
                "title": "AI短剧：剧本、分镜、人物、视频、配音、剪辑全流程",
                "source_type": "MARKETING",
                "medium": "VIDEO",
                "locator": "https://www.bilibili.com/video/BV1n3Vz6LEVS/",
                "published_at": "2026-06-02",
                "captured_at": "2026-08-21",
                "content": "视频标题宣称零基础学完即可接单变现；课程目录覆盖剧本、角色、场景、分镜、视频、配音音效和剪辑。",
                "notes": "带有资料领取与变现承诺，按营销材料处理。",
            },
            {
                "source_id": "BILI-PROMOTION-TUTORIAL",
                "title": "短剧推广项目：授权、收益、流程、剪辑和发布",
                "source_type": "EXPERT_INTERPRETATION",
                "medium": "VIDEO",
                "locator": "https://www.bilibili.com/video/BV1QryeBtEGv/",
                "published_at": "2025-10-31",
                "captured_at": "2026-08-21",
                "content": "发布者把短剧推广描述为：授权后剪辑片段并发布，为指定APP拉新以赚取佣金。",
                "notes": "这是发布者对推广模式的说明，未由相应推广平台规则交叉验证。",
            },
            {
                "source_id": "BILI-EARNING-2300",
                "title": "实测月赚2k+：海外短剧推广",
                "source_type": "ANECDOTE",
                "medium": "VIDEO",
                "locator": "https://www.bilibili.com/video/BV1NahvzTEYn/",
                "published_at": "2025-08-30",
                "captured_at": "2026-08-21",
                "content": "发布者自述：每天花1小时用电脑操作，这个月多赚2300+。",
                "notes": "个人自述，缺少后台原始数据、成本和可复现样本。",
            },
            {
                "source_id": "BILI-EARNING-20K",
                "title": "短剧推广项目拆解：小白也可以月入2w+",
                "source_type": "MARKETING",
                "medium": "VIDEO",
                "locator": "https://www.bilibili.com/video/BV1Wr421H7oz/",
                "published_at": "2024-03-12",
                "captured_at": "2026-08-21",
                "content": "视频标题宣称短剧推广小白也可以月入2w+。",
                "notes": "收入承诺型标题，按营销材料处理。",
            },
            {
                "source_id": "BILI-SCAM-WARNING",
                "title": "短剧版权剪辑骗局与短剧分红资金盘骗局",
                "source_type": "OPINION",
                "medium": "VIDEO",
                "locator": "https://www.bilibili.com/video/BV1rwdjBHEdE/",
                "published_at": "2026-04-20",
                "captured_at": "2026-08-21",
                "content": "发布者提醒：短剧版权剪辑、短剧分红和短剧投资项目中存在骗局风险。",
                "notes": "风险提醒，不等于对所有具体项目的司法认定。",
            },
            {
                "source_id": "YT-YPP-ELIGIBILITY",
                "title": "YouTube Partner Program overview and eligibility",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "ARTICLE",
                "locator": "https://support.google.com/youtube/answer/72851",
                "captured_at": "2026-08-21",
                "content": "Full ad-share threshold: 1,000 subscribers plus 4,000 watch hours / 12 months, or 10 million Shorts views / 90 days.",
                "notes": "从YouTube官方页面结构化提取的门槛事实。",
            },
            {
                "source_id": "YT-REVENUE-SHARES",
                "title": "YouTube partner earnings overview",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "ARTICLE",
                "locator": "https://support.google.com/youtube/answer/72902",
                "captured_at": "2026-08-21",
                "content": "Watch Page: 55% net. Shorts: 45% allocated. Fan funding: 70% net.",
                "notes": "从YouTube官方页面结构化提取的分成比例。",
            },
            {
                "source_id": "YT-MONETIZATION-POLICY",
                "title": "YouTube channel monetization policies",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "ARTICLE",
                "locator": "https://support.google.com/youtube/answer/1311392",
                "captured_at": "2026-08-21",
                "content": "Mass-produced or repetitive content is inauthentic and has always been ineligible for monetization.",
                "notes": "YouTube官方频道变现政策短摘录。",
            },
            {
                "source_id": "YT-AI-DISCLOSURE",
                "title": "Disclosing use of GenAI content",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "ARTICLE",
                "locator": "https://support.google.com/youtube/answer/14328491",
                "captured_at": "2026-08-21",
                "content": "Realistic generated or meaningfully altered content requires disclosure. Disclosure itself does not limit monetization eligibility.",
                "notes": "YouTube官方AI内容披露规则的结构化摘录。",
            },
            {
                "source_id": "BILI-CHARGE-RULES",
                "title": "哔哩哔哩充电计划用户协议",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "DOCUMENT",
                "locator": "https://www.bilibili.com/blackboard/charge-privacy.html",
                "captured_at": "2026-08-21",
                "content": "用户可以在充电面板支付B币为UP主充电。UP主应拥有发布内容的合法权利或全部合法授权。",
                "notes": "B站官方充电计划协议短摘录。",
            },
            {
                "source_id": "BILI-HUAHUO-FAQ",
                "title": "花火商单平台UP主入驻常见问题",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "DOCUMENT",
                "locator": "https://www.bilibili.com/blackboard/activity-zWUGlzmXPK.html",
                "captured_at": "2026-08-21",
                "content": "入驻要求：实名认证且年满18岁；粉丝不少于1万；近30天发布原创视频；创作分和影响分不低于70，信用分不低于90。",
                "notes": "B站官方花火FAQ的结构化摘录。",
            },
            {
                "source_id": "NRTA-NOTICE-2025",
                "title": "关于进一步统筹发展和安全促进网络微短剧行业健康繁荣发展的通知",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "DOCUMENT",
                "locator": "https://www.nrta.gov.cn/art/2025/2/5/art_113_70148.html",
                "published_at": "2025-02-05",
                "captured_at": "2026-08-21",
                "content": "网络视听平台、小程序、投流方等播出或引流、推送的所有微短剧，均须持有《网络剧片发行许可证》或完成相应上线报备登记程序。",
                "notes": "国家广播电视总局官方通知。",
            },
            {
                "source_id": "NRTA-MEASURES-2026",
                "title": "微短剧发展管理办法",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "DOCUMENT",
                "locator": "https://www.nrta.gov.cn/art/2026/7/31/art_1588_73827.html",
                "published_at": "2026-07-31",
                "captured_at": "2026-08-21",
                "content": "未取得发行许可证、批准文件或节目编号的微短剧不得播出。本办法自2026年9月1日起施行。",
                "notes": "已公布、尚未到施行日的国家广播电视总局部门规章。",
            },
            {
                "source_id": "DRAMABOX-JP-CREATORS",
                "title": "DramaBox短剧征集与分发说明",
                "source_type": "OFFICIAL_DOCUMENTATION",
                "medium": "ARTICLE",
                "locator": "https://www.dramabox.jp/creators",
                "captured_at": "2026-08-21",
                "content": "募集対象は15-100話のショートドラマ。収益分配は基本的にMG+レベニューシェアで、詳細は契約による。",
                "notes": "DramaBox日本站创作者页面；条款仅代表该页面和具体签约场景。",
            },
        ],
    }


def build_claims(bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    texts = {source["source_id"]: source["content"] for source in bundle["sources"]}
    cases = [
        dict(
            claim_id="SD-PROD-001",
            text="短片前期计划的三份基础文件是剧本、拍摄计划和预算。",
            operator="FACT",
            subject="短片前期计划的三份基础文件",
            predicate="是",
            object_="剧本、拍摄计划和预算",
            source_id="GUIDE-STUDIOBINDER-2025",
            source_kind="primary_source",
            evidence_fragment="The Screenplay; The Schedule; The Budget",
        ),
        dict(
            claim_id="SD-PROD-002",
            text="短片前期制作包括拆分剧本、准备镜头清单或分镜、排期、组建演员与团队以及落实场地。",
            operator="FACT",
            subject="短片前期制作",
            predicate="包括",
            object_="拆分剧本、准备镜头清单或分镜、排期、组建演员与团队以及落实场地",
            source_id="GUIDE-STUDIOBINDER-2025",
            source_kind="primary_source",
            evidence_fragment=(
                "Breaking down the script; Shot listing and/or storyboarding; Scheduling production; "
                "Hiring cast and crew; Securing shoot locations"
            ),
        ),
        dict(
            claim_id="SD-YT-001",
            text="YouTube完整广告分成门槛可以通过一千订阅加近十二个月四千小时公开观看时长，或一千订阅加近九十天一千万次有效Shorts公开观看达到。",
            operator="FACT",
            subject="YouTube完整广告分成门槛",
            predicate="可以通过",
            object_="一千订阅加近十二个月四千小时公开观看时长，或一千订阅加近九十天一千万次有效Shorts公开观看达到",
            source_id="YT-YPP-ELIGIBILITY",
            source_kind="official_documentation",
            evidence_fragment=(
                "1,000 subscribers plus 4,000 watch hours / 12 months, or 10 million Shorts views / 90 days"
            ),
        ),
        dict(
            claim_id="SD-YT-002",
            text="YouTube合作伙伴的观看页广告净收入分成为百分之五十五。",
            operator="FACT",
            subject="YouTube合作伙伴的观看页广告净收入分成",
            predicate="为",
            object_="百分之五十五",
            source_id="YT-REVENUE-SHARES",
            source_kind="official_documentation",
            evidence_fragment="Watch Page: 55% net",
        ),
        dict(
            claim_id="SD-YT-003",
            text="YouTube合作伙伴获得分配后Shorts收入的百分之四十五。",
            operator="FACT",
            subject="YouTube合作伙伴",
            predicate="获得",
            object_="分配后Shorts收入的百分之四十五",
            source_id="YT-REVENUE-SHARES",
            source_kind="official_documentation",
            evidence_fragment="Shorts: 45% allocated",
        ),
        dict(
            claim_id="SD-YT-004",
            text="YouTube合作伙伴的粉丝资助净收入分成为百分之七十。",
            operator="FACT",
            subject="YouTube合作伙伴的粉丝资助净收入分成",
            predicate="为",
            object_="百分之七十",
            source_id="YT-REVENUE-SHARES",
            source_kind="official_documentation",
            evidence_fragment="Fan funding: 70% net",
        ),
        dict(
            claim_id="SD-YT-005",
            text="YouTube把批量生产或重复内容归为不真实内容，并规定这类内容不符合变现条件。",
            operator="FACT",
            subject="YouTube",
            predicate="把批量生产或重复内容归为",
            object_="不真实内容，并规定这类内容不符合变现条件",
            source_id="YT-MONETIZATION-POLICY",
            source_kind="official_documentation",
            evidence_fragment=(
                "Mass-produced or repetitive content is inauthentic and has always been ineligible for monetization"
            ),
        ),
        dict(
            claim_id="SD-YT-006",
            text="YouTube要求披露看起来真实的AI生成内容或经过实质性AI修改的内容。",
            operator="FACT",
            subject="YouTube",
            predicate="要求披露",
            object_="看起来真实的AI生成内容或经过实质性AI修改的内容",
            source_id="YT-AI-DISCLOSURE",
            source_kind="official_documentation",
            evidence_fragment="Realistic generated or meaningfully altered content requires disclosure",
        ),
        dict(
            claim_id="SD-YT-007",
            text="在YouTube正确披露AI内容本身不会限制该内容的变现资格。",
            operator="FACT",
            subject="在YouTube正确披露AI内容本身",
            predicate="不会限制",
            object_="该内容的变现资格",
            source_id="YT-AI-DISCLOSURE",
            source_kind="official_documentation",
            evidence_fragment="Disclosure itself does not limit monetization eligibility",
        ),
        dict(
            claim_id="SD-BILI-001",
            text="B站充电计划允许用户在充电面板支付B币支持UP主。",
            operator="FACT",
            subject="B站充电计划",
            predicate="允许",
            object_="用户在充电面板支付B币支持UP主",
            source_id="BILI-CHARGE-RULES",
            source_kind="official_documentation",
            evidence_fragment="用户可以在充电面板支付B币为UP主充电",
        ),
        dict(
            claim_id="SD-BILI-002",
            text="参与B站充电计划的UP主应拥有发布内容的合法权利或全部合法授权。",
            operator="FACT",
            subject="参与B站充电计划的UP主",
            predicate="应拥有",
            object_="发布内容的合法权利或全部合法授权",
            source_id="BILI-CHARGE-RULES",
            source_kind="official_documentation",
            evidence_fragment="UP主应拥有发布内容的合法权利或全部合法授权",
        ),
        dict(
            claim_id="SD-BILI-003",
            text="B站花火当前要求个人UP主实名认证且年满十八岁、粉丝不少于一万、近三十天发布过原创视频，并达到规定的电磁力分数。",
            operator="FACT",
            subject="B站花火当前",
            predicate="要求",
            object_="实名认证且年满十八岁、粉丝不少于一万、近三十天发布过原创视频，并达到规定的电磁力分数",
            source_id="BILI-HUAHUO-FAQ",
            source_kind="official_documentation",
            evidence_fragment=(
                "实名认证且年满18岁；粉丝不少于1万；近30天发布原创视频；创作分和影响分不低于70，信用分不低于90"
            ),
        ),
        dict(
            claim_id="SD-CN-001",
            text="在中国境内由网络视听平台、小程序或投流方播出、引流或推送的微短剧，须持有网络剧片发行许可证或完成相应上线报备登记程序。",
            operator="FACT",
            subject="在中国境内由网络视听平台、小程序或投流方播出、引流或推送的微短剧",
            predicate="须",
            object_="持有网络剧片发行许可证或完成相应上线报备登记程序",
            source_id="NRTA-NOTICE-2025",
            source_kind="official_record",
            evidence_fragment="所有微短剧，均须持有《网络剧片发行许可证》或完成相应上线报备登记程序",
        ),
        dict(
            claim_id="SD-CN-002",
            text="《微短剧发展管理办法》规定未取得发行许可证、批准文件或节目编号的微短剧不得播出。",
            operator="FACT",
            subject="《微短剧发展管理办法》",
            predicate="规定",
            object_="未取得发行许可证、批准文件或节目编号的微短剧不得播出",
            source_id="NRTA-MEASURES-2026",
            source_kind="official_record",
            evidence_fragment="未取得发行许可证、批准文件或节目编号的微短剧不得播出",
        ),
        dict(
            claim_id="SD-CN-003",
            text="《微短剧发展管理办法》自二〇二六年九月一日起施行。",
            operator="FACT",
            subject="《微短剧发展管理办法》",
            predicate="自二〇二六年九月一日起",
            object_="施行",
            source_id="NRTA-MEASURES-2026",
            source_kind="official_record",
            evidence_fragment="本办法自2026年9月1日起施行",
        ),
        dict(
            claim_id="SD-DIST-001",
            text="DramaBox日本创作者页面接受十五至一百集的短剧作品进行分发洽谈。",
            operator="FACT",
            subject="DramaBox日本创作者页面",
            predicate="接受",
            object_="十五至一百集的短剧作品进行分发洽谈",
            source_id="DRAMABOX-JP-CREATORS",
            source_kind="official_documentation",
            evidence_fragment="募集対象は15-100話のショートドラマ",
        ),
        dict(
            claim_id="SD-DIST-002",
            text="DramaBox日本创作者页面所述的基本收益方式是最低保底加收入分成，具体条件以合同为准。",
            operator="FACT",
            subject="DramaBox日本创作者页面所述的基本收益方式",
            predicate="是",
            object_="最低保底加收入分成，具体条件以合同为准",
            source_id="DRAMABOX-JP-CREATORS",
            source_kind="official_documentation",
            evidence_fragment="収益分配は基本的にMG+レベニューシェアで、詳細は契約による",
        ),
        dict(
            claim_id="SD-VIEW-001",
            text="B站创作者把画面、运镜、景别、时长、台词、声音、转场和道具列为拍摄脚本字段。",
            operator="OBSERVE",
            subject="B站创作者",
            predicate="把",
            object_="画面、运镜、景别、时长、台词、声音、转场和道具列为拍摄脚本字段",
            source_id="BILI-STORYBOARD",
            source_kind="primary_source",
            evidence_fragment=(
                "拍摄脚本一般包含画面内容、镜头运动、景别、长度、台词、音乐音效、转场方式和道具"
            ),
        ),
        dict(
            claim_id="SD-VIEW-002",
            text="B站教程发布者把短剧推广描述为授权后剪辑片段并发布，为指定应用拉新以赚取佣金。",
            operator="OBSERVE",
            subject="B站教程发布者",
            predicate="把短剧推广描述为",
            object_="授权后剪辑片段并发布，为指定应用拉新以赚取佣金",
            source_id="BILI-PROMOTION-TUTORIAL",
            source_kind="primary_source",
            evidence_fragment="授权后剪辑片段并发布，为指定APP拉新以赚取佣金",
        ),
        dict(
            claim_id="SD-VIEW-003",
            text="B站视频发布者自述每天花一小时做海外短剧推广，当月多赚二千三百元以上。",
            operator="OBSERVE",
            subject="B站视频发布者",
            predicate="自述",
            object_="每天花一小时做海外短剧推广，当月多赚二千三百元以上",
            source_id="BILI-EARNING-2300",
            source_kind="primary_source",
            evidence_fragment="每天花1小时用电脑操作，这个月多赚2300+",
        ),
        dict(
            claim_id="SD-VIEW-004",
            text="D4Darious的视频简介称该视频讨论短片写作中的背景故事管理和应避免的问题。",
            operator="OBSERVE",
            subject="D4Darious的视频简介",
            predicate="称",
            object_="该视频讨论短片写作中的背景故事管理和应避免的问题",
            source_id="YT-D4DARIOUS-TIPS",
            source_kind="primary_source",
            evidence_fragment="managing backstory and what to avoid in the writing process",
        ),
        dict(
            claim_id="SD-VIEW-005",
            text="B站视频发布者提醒短剧版权剪辑、分红和投资项目中存在骗局风险。",
            operator="OBSERVE",
            subject="B站视频发布者",
            predicate="提醒",
            object_="短剧版权剪辑、分红和投资项目中存在骗局风险",
            source_id="BILI-SCAM-WARNING",
            source_kind="primary_source",
            evidence_fragment="短剧版权剪辑、短剧分红和短剧投资项目中存在骗局风险",
        ),
        dict(
            claim_id="SD-HOLD-001",
            text="零基础用户学完一套AI短剧教程即可接单变现。",
            operator="FACT",
            subject="零基础用户",
            predicate="学完一套AI短剧教程即可",
            object_="接单变现",
            source_id="BILI-AI-COURSE",
            source_kind="marketing_copy",
            evidence_fragment="零基础学完即可接单变现",
        ),
        dict(
            claim_id="SD-HOLD-002",
            text="短剧推广适合普通新手稳定月入二万元以上。",
            operator="FACT",
            subject="短剧推广",
            predicate="适合普通新手稳定",
            object_="月入二万元以上",
            source_id="BILI-EARNING-20K",
            source_kind="marketing_copy",
            evidence_fragment="短剧推广小白也可以月入2w+",
        ),
        dict(
            claim_id="SD-HOLD-003",
            text="普通人每天花一小时做海外短剧推广都能月赚二千三百元以上。",
            operator="FACT",
            subject="普通人",
            predicate="每天花一小时做海外短剧推广都能",
            object_="月赚二千三百元以上",
            source_id="BILI-EARNING-2300",
            source_kind="unsupported_assertion",
            evidence_fragment="每天花1小时用电脑操作，这个月多赚2300+",
        ),
        dict(
            claim_id="SD-REJECT-001",
            text="无需获得版权或授权也可以剪辑他人短剧并在B站发布获利。",
            operator="FACT",
            subject="剪辑他人短剧并在B站发布获利",
            predicate="无需获得",
            object_="版权或授权",
            source_id="BILI-CHARGE-RULES",
            source_kind="official_documentation",
            evidence_fragment="UP主应拥有发布内容的合法权利或全部合法授权",
            relation="CONTRADICTS",
        ),
        dict(
            claim_id="SD-REJECT-002",
            text="批量生成重复模板化AI短剧就能稳定通过YouTube频道变现审核。",
            operator="FACT",
            subject="批量生成重复模板化AI短剧",
            predicate="就能稳定通过",
            object_="YouTube频道变现审核",
            source_id="YT-MONETIZATION-POLICY",
            source_kind="official_documentation",
            evidence_fragment=(
                "Mass-produced or repetitive content is inauthentic and has always been ineligible for monetization"
            ),
            relation="CONTRADICTS",
        ),
    ]
    return [single_evidence_claim(source_text=texts[item["source_id"]], **item) for item in cases]


def write_json(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    bundle = build_source_bundle()
    validate_source_bundle(bundle, CASE_DIR)
    write_json(CASE_DIR / "source-bundle.json", bundle)

    claim_dir = CASE_DIR / "claims"
    certificate_dir = CASE_DIR / "certificates"
    claim_dir.mkdir(exist_ok=True)
    certificate_dir.mkdir(exist_ok=True)
    certificates: Dict[str, Dict[str, Any]] = {}
    for payload in build_claims(bundle):
        claim_id = payload["claim_ir"]["claim_id"]
        write_json(claim_dir / f"{claim_id}.json", payload)
        certificate = compile_claim(payload)
        certificates[claim_id] = certificate
        write_json(certificate_dir / f"{claim_id}.json", certificate)

    source_view = [
        {
            key: source[key]
            for key in ("source_id", "title", "source_type", "medium", "locator")
        }
        for source in bundle["sources"]
    ]

    explanations = {
        "SD-PROD-001": ("制作基础", "权威制作指南明确列出三份基础文件。", [], ["这是通用短片前期框架，不等于短剧题材与商业成功公式。"]),
        "SD-PROD-002": ("制作基础", "权威制作指南逐项列出这些前期任务。", [], ["AI流程可以替换部分执行工具，但不会自动消除计划、版权和质量控制。"]),
        "SD-YT-001": ("YouTube变现", "YouTube官方YPP页面给出完整广告分成门槛。", ["频道仍需通过政策审核。"], ["达到数字门槛不保证申请通过，也不保证收入水平。"]),
        "SD-YT-002": ("YouTube变现", "YouTube官方收益说明给出观看页广告分成比例。", ["需要加入YPP并接受对应模块。"], ["实际收入取决于有效观看、地区、广告需求等因素。"]),
        "SD-YT-003": ("YouTube变现", "YouTube官方收益说明给出Shorts分配后收入比例。", ["先按Creator Pool规则分配，再应用45%比例。"], ["45%不是每次播放的固定单价。"]),
        "SD-YT-004": ("YouTube变现", "YouTube官方收益说明给出粉丝资助净收入比例。", ["需要满足相应功能资格并接受Commerce Product Module。"], ["粉丝是否付费取决于真实受众关系。"]),
        "SD-YT-005": ("YouTube风险", "YouTube官方频道变现政策直接规定批量、重复内容不符合变现要求。", [], ["使用AI本身不是问题，模板化、低差异和缺少原创价值才是关键风险。"]),
        "SD-YT-006": ("YouTube风险", "YouTube官方AI披露规则要求披露逼真或实质性修改内容。", ["适用于看起来真实的生成或实质性修改内容。"], ["仍需同时遵守版权、社区与广告友好规则。"]),
        "SD-YT-007": ("YouTube风险", "YouTube官方说明确认正确披露本身不降低变现资格。", [], ["不代表该内容自动符合其他变现政策。"]),
        "SD-BILI-001": ("B站变现", "B站官方充电协议确认了观众直接支持渠道。", ["UP主需开通充电计划并满足平台流程。"], ["存在功能不等于观众会付费。"]),
        "SD-BILI-002": ("版权", "B站官方协议明确要求合法权利或完整授权。", [], ["具体素材还可能涉及音乐、字体、肖像、声音和AI训练/生成条款。"]),
        "SD-BILI-003": ("B站变现", "B站官方花火FAQ列出当前入驻条件。", ["规则会变化，应在接单前重新核对。"], ["入驻只是获得商单工具资格，不保证获得订单。"]),
        "SD-CN-001": ("中国发行合规", "国家广电总局官方通知给出当前上线前审核备案要求。", ["适用于中国境内网络微短剧传播。"], ["不同投资规模与传播方式对应的申报层级不同。"]),
        "SD-CN-002": ("中国发行合规", "已公布的部门规章给出许可证、批准文件或节目编号要求。", ["该办法自2026-09-01起施行。"], ["申报类别和实施细则需要结合项目所在地与播出平台确认。"]),
        "SD-CN-003": ("中国发行合规", "国家广电总局正式公布了施行日期。", [], ["本案例检索日是2026-08-21，施行日尚未到。"]),
        "SD-DIST-001": ("专业平台分发", "DramaBox日本官方创作者页面给出接收的集数范围。", ["仅代表该日本站页面与洽谈入口。"], ["提交样片不等于签约或上线。"]),
        "SD-DIST-002": ("专业平台分发", "DramaBox日本官方页面说明基本收益结构。", ["具体比例、费用、独占性和权利范围以合同为准。"], ["MG并非所有项目都必然获得的固定收入。"]),
        "SD-VIEW-001": ("制作经验", "证书只确认该B站创作者给出了这组脚本字段。", [], ["这是实务模板，不是唯一正确格式。"]),
        "SD-VIEW-002": ("推广经验", "证书只确认发布者这样描述短剧推广模式。", ["发布者明确提到先取得授权。"], ["佣金规则、平台资格和实际转化率未被独立核验。"]),
        "SD-VIEW-003": ("收入个案", "证书只确认发布者做过该收入自述。", [], ["没有核验成本、失败样本、账号基数和后台原始数据。"]),
        "SD-VIEW-004": ("制作经验", "证书只确认YouTube视频简介声明了这些讨论内容。", [], ["没有完整字幕，因此不把具体建议扩写成知识。"]),
        "SD-VIEW-005": ("风险观点", "证书只确认发布者发出了骗局风险提醒。", [], ["不能据此认定某个具体项目违法或诈骗。"]),
        "SD-HOLD-001": ("收入承诺", "唯一依据是带资料导流和变现承诺的课程营销页面。", [], ["缺少真实订单、报价、获客成本、交付能力和失败率。"]),
        "SD-HOLD-002": ("收入承诺", "唯一依据是收入承诺型视频标题。", [], ["缺少样本范围、时间成本、投流成本、账号存活率和后台数据。"]),
        "SD-HOLD-003": ("收入外推", "一个人的自述不能外推到普通人。", [], ["需要多账号、完整成本与时间窗口的可审计记录。"]),
        "SD-REJECT-001": ("版权红线", "B站官方协议与“无需授权”的说法直接冲突。", [], ["其他平台和素材类型还需要核对各自授权条款。"]),
        "SD-REJECT-002": ("YouTube红线", "YouTube官方政策与“模板化批量内容稳定通过变现”的说法直接冲突。", [], ["原创、内容差异和观众价值仍需要人工与平台审核。"]),
    }

    viewpoint_ids = {f"SD-VIEW-{index:03d}" for index in range(1, 6)}
    hold_ids = {f"SD-HOLD-{index:03d}" for index in range(1, 4)}
    reject_ids = {f"SD-REJECT-{index:03d}" for index in range(1, 3)}
    claim_sources = {
        payload["claim_ir"]["claim_id"]: [item["source_id"] for item in payload["evidence"]]
        for payload in build_claims(bundle)
    }
    records = []
    for claim_id, certificate in certificates.items():
        topic, explanation, conditions, limitations = explanations[claim_id]
        if claim_id in viewpoint_ids:
            layer = "PRACTICE_OR_VIEWPOINT"
            text = certificate["canonical_claim"]
        elif claim_id in hold_ids:
            layer = "DISPUTED_OR_UNRESOLVED"
            text = certificate["claim_text"]
        elif claim_id in reject_ids:
            layer = "REJECTED"
            text = certificate["claim_text"]
        else:
            layer = "SUPPORTED_KNOWLEDGE"
            text = certificate["canonical_claim"]
        records.append(
            {
                "record_id": f"DOC-{claim_id}",
                "topic": topic,
                "layer": layer,
                "text": text,
                "explanation": explanation,
                "source_ids": claim_sources[claim_id],
                "conditions": conditions,
                "limitations": limitations,
                "certificate_file": f"certificates/{claim_id}.json",
            }
        )

    plan = {
        "document_version": "1.0",
        "title": "做短剧并赚钱：经过过滤的知识地图",
        "question": bundle["question"],
        "language": "zh-CN",
        "source_boundary": bundle["source_boundary"],
        "sources": source_view,
        "records": records,
        "open_questions": [
            "B站与YouTube短剧账号在不同题材、地区和时长下的真实RPM、完播率和付费率分布是什么？",
            "专业短剧平台对独立创作者的签约率、MG范围、分账周期和回本率是什么？",
            "真人短剧与AI短剧在相同剧本和投放条件下的完播、复看、获客成本和制作成本如何比较？",
            "短剧推广项目的授权链、结算后台、退款与封号率能否获得可审计样本？",
        ],
    }
    write_json(CASE_DIR / "knowledge-document.json", plan)
    (CASE_DIR / "RESULT.md").write_text(
        render_knowledge_document(plan, CASE_DIR), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
