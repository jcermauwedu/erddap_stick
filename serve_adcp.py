import xarray as xr
import xpublish

ds = xr.open_dataset('gcoos_ioos-station-wmo-42874_2024_05.nc')

ds.rest(
    app_kws=dict(
        title="GCOOS IOOS Station WMO 42874 2024_05",
        description="ADCP Profiles for WMO 42874",
        openapi_url="/wmo42874.JSON",
    ),
    cache_kws=dict(available_bytes=1e9),
)

ds.rest.serve()

#rest = xpublish.SingleDatasetRest(ds)
#rest.serve()
