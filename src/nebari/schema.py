import enum
import sys

import pydantic
from pydantic import ConfigDict, Field, StringConstraints, field_validator
from ruamel.yaml import yaml_object

from _nebari.utils import escape_string, yaml
from _nebari.version import __version__, rounded_ver_parse

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated


# Regex for suitable project names
namestr_regex = r"^[A-Za-z][A-Za-z\-_]*[A-Za-z]$"
letter_dash_underscore_pydantic = Annotated[
    str, StringConstraints(pattern=namestr_regex)
]

email_regex = "^[^ @]+@[^ @]+\\.[^ @]+$"
email_pydantic = Annotated[str, StringConstraints(pattern=email_regex)]


class Base(pydantic.BaseModel):
    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, populate_by_name=True
    )


@yaml_object(yaml)
class ProviderEnum(str, enum.Enum):
    local = "local"
    existing = "existing"
    do = "do"
    aws = "aws"
    gcp = "gcp"
    azure = "azure"

    @classmethod
    def to_yaml(cls, representer, node):
        return representer.represent_str(node.value)


class Main(Base):
    project_name: letter_dash_underscore_pydantic = "project-name"
    namespace: letter_dash_underscore_pydantic = "dev"
    provider: ProviderEnum = ProviderEnum.local
    # In nebari_version only use major.minor.patch version - drop any pre/post/dev suffixes
    nebari_version: Annotated[str, Field(validate_default=True)] = __version__

    prevent_deploy: bool = (
        False  # Optional, but will be given default value if not present
    )

    # If the nebari_version in the schema is old
    # we must tell the user to first run nebari upgrade
    @field_validator("nebari_version")
    @classmethod
    def check_default(cls, v):
        """
        Always called even if nebari_version is not supplied at all (so defaults to ''). That way we can give a more helpful error message.
        """
        if not cls.is_version_accepted(v):
            if v == "":
                v = "not supplied"
            raise ValueError(
                f"nebari_version in the config file must be equivalent to {__version__} to be processed by this version of nebari (your config file version is {v})."
                " Install a different version of nebari or run nebari upgrade to ensure your config file is compatible."
            )
        return v

    @classmethod
    def is_version_accepted(cls, v):
        return v != "" and rounded_ver_parse(v) == rounded_ver_parse(__version__)

    @property
    def escaped_project_name(self):
        """Escaped project-name know to be compatible with all clouds"""
        project_name = self.project_name

        if self.provider == ProviderEnum.azure and "-" in project_name:
            project_name = escape_string(project_name, escape_char="a")

        if self.provider == ProviderEnum.aws and project_name.startswith("aws"):
            project_name = "a" + project_name

        if len(project_name) > 16:
            project_name = project_name[:16]

        return project_name


def is_version_accepted(v):
    """
    Given a version string, return boolean indicating whether
    nebari_version in the nebari-config.yaml would be acceptable
    for deployment with the current Nebari package.
    """
    return Main.is_version_accepted(v)