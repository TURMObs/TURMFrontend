from django.core.management.base import BaseCommand
from observation_data.models import (
    Observatory,
    ExposureSettings,
    ObservatoryExposureSettings,
    ObservationType,
    Filter,
)


class Command(BaseCommand):
    help = "Populate the observatories, exposure settings and filters in the database."

    def handle(self, *args, **options):
        """
        This command adds the observatories, exposure settings and filters to the database.
        """
        self.populate_observatories()
        self.populate_exposure_settings()
        self.populate_filters()

    @staticmethod
    def populate_observatories():
        Observatory.objects.get_or_create(
            name="TURMX",
            defaults={
                "horizon_offset": 0.0,
                "min_stars": -1,
                "max_HFR": 4.0,
                "max_guide_error": 1000.0,
            },
        )

        Observatory.objects.get_or_create(
            name="TURMX2",
            defaults={
                "horizon_offset": 0.0,
                "min_stars": -1,
                "max_HFR": 6.0,
                "max_guide_error": 1000.0,
            },
        )

    @staticmethod
    def populate_exposure_settings():
        ExposureSettings.objects.get_or_create(
            gain=100, offset=50, binning=1, subFrame=1.0
        )

        ExposureSettings.objects.get_or_create(
            gain=2750, offset=0, binning=1, subFrame=1.0
        )

        ExposureSettings.objects.get_or_create(
            gain=0, offset=50, binning=1, subFrame=0.25
        )

        ExposureSettings.objects.get_or_create(
            gain=0, offset=0, binning=1, subFrame=0.5
        )

        ObservatoryExposureSettings.objects.get_or_create(
            observatory=Observatory.objects.get(name="TURMX"),
            exposure_settings=ExposureSettings.objects.get(
                gain=100, offset=50, binning=1, subFrame=1.0
            ),
            observation_type=ObservationType.IMAGING,
        )

        ObservatoryExposureSettings.objects.get_or_create(
            observatory=Observatory.objects.get(name="TURMX2"),
            exposure_settings=ExposureSettings.objects.get(
                gain=2750, offset=0, binning=1, subFrame=1.0
            ),
            observation_type=ObservationType.IMAGING,
        )

        for observation_type in [
            ObservationType.EXOPLANET,
            ObservationType.VARIABLE,
            ObservationType.MONITORING,
        ]:
            ObservatoryExposureSettings.objects.get_or_create(
                observatory=Observatory.objects.get(name="TURMX"),
                exposure_settings=ExposureSettings.objects.get(
                    gain=0, offset=50, binning=1, subFrame=0.25
                ),
                observation_type=observation_type,
            )
            ObservatoryExposureSettings.objects.get_or_create(
                observatory=Observatory.objects.get(name="TURMX2"),
                exposure_settings=ExposureSettings.objects.get(
                    gain=0, offset=0, binning=1, subFrame=0.5
                ),
                observation_type=observation_type,
            )

    @staticmethod
    def populate_filters():
        for filter_type in [
            Filter.FilterType.LUMINANCE,
            Filter.FilterType.RED,
            Filter.FilterType.GREEN,
            Filter.FilterType.BLUE,
        ]:
            Filter.objects.get_or_create(
                filter_type=filter_type,
                moon_separation_angle=100,
                moon_separation_width=7,
            )

        for filter_type in [
            Filter.FilterType.HYDROGEN,
            Filter.FilterType.OXYGEN,
            Filter.FilterType.SULFUR,
        ]:
            Filter.objects.get_or_create(
                filter_type=filter_type,
                moon_separation_angle=70,
                moon_separation_width=7,
            )

        for filter_type in [
            Filter.FilterType.SR,
            Filter.FilterType.SG,
            Filter.FilterType.SI,
        ]:
            Filter.objects.get_or_create(
                filter_type=filter_type,
                moon_separation_angle=50,
                moon_separation_width=7,
            )

        # link filters to observatories
        turmx = Observatory.objects.get(name="TURMX")
        turmx2 = Observatory.objects.get(name="TURMX2")
        for filter_type in [
            Filter.FilterType.LUMINANCE,
            Filter.FilterType.RED,
            Filter.FilterType.GREEN,
            Filter.FilterType.BLUE,
            Filter.FilterType.HYDROGEN,
            Filter.FilterType.OXYGEN,
            Filter.FilterType.SULFUR,
        ]:
            turmx.filter_set.add(Filter.objects.get(filter_type=filter_type))
            turmx2.filter_set.add(Filter.objects.get(filter_type=filter_type))
        for filter_type in [
            Filter.FilterType.SR,
            Filter.FilterType.SG,
            Filter.FilterType.SI,
        ]:
            turmx2.filter_set.add(Filter.objects.get(filter_type=filter_type))
