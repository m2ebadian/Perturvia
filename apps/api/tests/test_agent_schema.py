import pytest
from pydantic import ValidationError

from app.schemas.agent import AgentCreate


def test_agent_name_strips_whitespace():
    agent = AgentCreate(name=" Test Agent ")
    assert agent.name == "Test Agent"


def test_agent_name_rejects_whitespace_only():
    with pytest.raises(ValidationError):
        AgentCreate(name=" ")


def test_agent_name_is_required():
    with pytest.raises(ValidationError):
        AgentCreate()


def test_agent_name_max_length_boundary():
    assert AgentCreate(name="a" * 255).name == "a" * 255
    with pytest.raises(ValidationError):
        AgentCreate(name="a" * 256)


def test_agent_name_length_checked_after_strip():
    agent = AgentCreate(name=" " + "a" * 255 + " ")
    assert agent.name == "a" * 255


def test_agent_description_defaults_to_none():
    assert AgentCreate(name="Test Agent").description is None
