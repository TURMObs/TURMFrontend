import json
import os

from django.core.management.base import BaseCommand, CommandError
from observation_data.models import (
    Observatory,
    ExposureSettings,
    ObservatoryExposureSettings,
    ObservationType,
    Filter,
)


class Command(BaseCommand):
    help = "Loads the observatories, exposure settings and filters into the database."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the configuration file.")
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete the database before loading the configuration.",
        )

        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite the existing configuration.",
        )

    def handle(self, *args, **options):
        """
        This command adds the observatories, exposure settings and filters to the database.
        """
        overwrite = options["overwrite"]
        delete = options["delete"]
        path = options["path"]
        if not os.path.exists(path):
            raise CommandError(f"File at {path} does not exist.")

        self.load_observatories(overwrite, delete, path)
        self.populate_exposure_settings(overwrite, delete, path)
        self.populate_filters()

    def load_observatories(self, overwrite, delete, path):
        if delete:
            Observatory.objects.all().delete()

        with open(path, "r") as f:
            data = json.load(f)

        created_observatories = []
        for observatory in data["observatories"]:
            if (
                not overwrite
                and Observatory.objects.filter(name=observatory["name"]).exists()
            ):
                self.stdout.write(
                    f"Observatory {observatory['name']} already exists. Set --overwrite to overwrite."
                )
                continue
            self.stdout.write(f"Created observatory {observatory['name']}.")
            obs = Observatory.objects.create(
                name=observatory["name"],
                horizon_offset=observatory["horizon_offset"],
                min_stars=observatory["min_stars"],
                max_HFR=observatory["max_HFR"],
                max_guide_error=observatory["max_guide_error"],
            )
            created_observatories.append(obs)

        untouched_observatories = Observatory.objects.exclude(
            pk__in=[obs.pk for obs in created_observatories]
        )
        for obs in untouched_observatories:
            self.stdout.write(f"Observatory {obs.name} existed and was not changed.")

    def populate_exposure_settings(self, overwrite, delete, path):
        if delete:
            ExposureSettings.objects.all().delete()
            ObservatoryExposureSettings.objects.all().delete()

        with open(path, "r") as f:
            data = json.load(f)

        created_exposure_settings = []
        for entry in data["exposure_settings"]:
            for (
                observatory_name,
                settings,
            ) in entry.items():  # Extract observatory name and settings
                if not Observatory.objects.filter(name=observatory_name).exists():
                    self.stdout.write(
                        f"Observatory {observatory_name} does not exist. Skipping exposure settings."
                    )
                    continue

                obs = Observatory.objects.get(name=observatory_name)

                for observation_type in [
                    ObservationType.IMAGING,
                    ObservationType.EXOPLANET,
                    ObservationType.VARIABLE,
                    ObservationType.MONITORING,
                ]:
                    if observation_type.name not in settings:
                        self.stdout.write(
                            f"Exposure settings for type {observation_type} not found for observatory {obs.name}!"
                        )
                        continue

                    exposure_data = settings[observation_type.name]
                    gain, offset, binning, subframe = (
                        exposure_data["gain"],
                        exposure_data["offset"],
                        exposure_data["binning"],
                        exposure_data["subframe"],
                    )

                    if (
                        not overwrite
                        and ObservatoryExposureSettings.objects.filter(
                            observatory=obs, observation_type=observation_type
                        ).exists()
                    ):
                        self.stdout.write(
                            f"Exposure settings for {observation_type} at {obs.name} already exist. Set --overwrite to overwrite."
                        )
                        continue

                    exposure_settings = ExposureSettings.objects.create(
                        gain=gain, offset=offset, binning=binning, subframe=subframe
                    )
                    created = ObservatoryExposureSettings.objects.create(
                        observatory=obs,
                        exposure_settings=exposure_settings,
                        observation_type=observation_type,
                    )
                    created_exposure_settings.append(created)
                    self.stdout.write(
                        f"Created exposure settings for {observation_type} at {obs.name}."
                    )

        untouched_exposure_settings = ObservatoryExposureSettings.objects.exclude(
            pk__in=[obs.pk for obs in created_exposure_settings]
        )
        for obs in untouched_exposure_settings:
            self.stdout.write(
                f"Exposure settings for {obs.observation_type} at {obs.observatory.name} existed and were not changed."
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
            Filter.FilterType.SLOAN_R,
            Filter.FilterType.SLOAN_G,
            Filter.FilterType.SLOAN_I,
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
            Filter.FilterType.SLOAN_R,
            Filter.FilterType.SLOAN_G,
            Filter.FilterType.SLOAN_I,
        ]:
            turmx2.filter_set.add(Filter.objects.get(filter_type=filter_type))
