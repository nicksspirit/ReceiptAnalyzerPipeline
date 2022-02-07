
def unpack_exc(ex: Exception) -> tuple[str, str]:
    ex_name = ex.__class__.__name__
    ex_msg = getattr(ex, "message", str(ex))

    return ex_name, ex_msg
