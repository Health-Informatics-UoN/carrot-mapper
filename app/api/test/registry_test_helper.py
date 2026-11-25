import uuid

from registry.models import CARROT_MAPPING_SET_NAMESPACE


def series_id_for(set_uri: str) -> uuid.UUID:
    """
    The id of a new series for ``set_uri``: the uuid a Carrot set_uri ends
    with ({CARROT_MAPPING_SET_NAMESPACE}{uuid}), else a random one. Mirrored
    by registry_import's series_id_for.
    """
    if set_uri.startswith(CARROT_MAPPING_SET_NAMESPACE):
        try:
            return uuid.UUID(set_uri[len(CARROT_MAPPING_SET_NAMESPACE) :].strip("/"))
        except ValueError:
            pass
    return uuid.uuid4()
