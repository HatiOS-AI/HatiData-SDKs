from dbt.adapters.hatidata.connections import HatiDataConnectionManager  # noqa: F401
from dbt.adapters.hatidata.connections import HatiDataCredentials  # noqa: F401
from dbt.adapters.hatidata.impl import HatiDataAdapter  # noqa: F401
from dbt.adapters.hatidata.relation import HatiDataRelation  # noqa: F401
from dbt.adapters.hatidata.column import HatiDataColumn  # noqa: F401

from dbt.adapters.base import AdapterPlugin

Plugin = AdapterPlugin(
    adapter=HatiDataAdapter,
    credentials=HatiDataCredentials,
    include_path=HatiDataAdapter.type(),
)
