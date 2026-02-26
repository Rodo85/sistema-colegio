from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("matricula", "0004_alter_matriculaacademica_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="matriculaacademica",
            name="origen_carga",
            field=models.CharField(
                choices=[("MANUAL", "Manual"), ("GENERAL_EXCEL", "General por Excel")],
                default="MANUAL",
                max_length=20,
                verbose_name="Origen de carga",
            ),
        ),
    ]
