# Generated by Django 5.2.3 on 2025-07-31 18:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('config_institucional', '0003_periodolectivo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='periodolectivo',
            name='anio',
            field=models.PositiveIntegerField(choices=[(2020, 2020), (2021, 2021), (2022, 2022), (2023, 2023), (2024, 2024), (2025, 2025), (2026, 2026), (2027, 2027), (2028, 2028), (2029, 2029), (2030, 2030)]),
        ),
    ]
