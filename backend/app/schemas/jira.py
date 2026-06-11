"""
Jira Schemas
Pydantic models for Jira integration
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class JiraConnection(BaseModel):
    """Jira connection configuration"""
    jira_url: str = Field(..., description="Jira instance URL")
    email: str = Field(..., description="User email for authentication")
    api_token: str = Field(..., description="Jira API token")


class JiraIssueField(BaseModel):
    """Jira issue field"""
    key: str
    value: Any


class JiraIssue(BaseModel):
    """Jira issue/ticket"""
    id: str
    key: str
    summary: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    issue_type: str
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    resolved: Optional[datetime] = None
    project_key: str
    project_name: str
    labels: List[str] = Field(default_factory=list)
    components: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class JiraProject(BaseModel):
    """Jira project"""
    id: str
    key: str
    name: str
    description: Optional[str] = None
    lead: Optional[str] = None
    project_type: Optional[str] = None
    issue_count: int = 0


class JiraStats(BaseModel):
    """Jira statistics"""
    total_issues: int = 0
    open_issues: int = 0
    in_progress_issues: int = 0
    resolved_issues: int = 0
    closed_issues: int = 0
    total_projects: int = 0
    last_sync: Optional[datetime] = None
    status_breakdown: Dict[str, int] = Field(default_factory=dict)


class JiraSyncRequest(BaseModel):
    """Request to sync Jira tickets"""
    project_keys: Optional[List[str]] = Field(None, description="Specific project keys to sync")
    jql: Optional[str] = Field(None, description="Custom JQL query")
    max_results: int = Field(100, description="Maximum number of tickets to fetch", ge=1, le=1000)
    include_resolved: bool = Field(True, description="Include resolved tickets")


class JiraSyncResponse(BaseModel):
    """Response from Jira sync"""
    success: bool
    issues_fetched: int
    issues_indexed: int
    projects: List[str]
    duration_seconds: float
    errors: List[str] = Field(default_factory=list)


class JiraTestConnectionResponse(BaseModel):
    """Response from test connection"""
    success: bool
    message: str
    server_info: Optional[Dict[str, Any]] = None
    projects_count: Optional[int] = None


class JiraSearchRequest(BaseModel):
    """Request to search Jira issues"""
    query: str = Field(..., description="Search query")
    project_keys: Optional[List[str]] = None
    status: Optional[List[str]] = None
    max_results: int = Field(50, ge=1, le=500)
    start_at: int = Field(0, ge=0, description="Pagination offset")


class JiraSearchResponse(BaseModel):
    """Response from Jira search"""
    issues: List[JiraIssue]
    total: int
    start_at: int
    max_results: int
