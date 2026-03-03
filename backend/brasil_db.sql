DROP TABLE encoding_correct;
CREATE TABLE encoding_correct (table_name CHARACTER VARYING NOT NULL, id BIGINT NOT NULL, column_backup TEXT, enc_id BIGINT DEFAULT nextval('encoding_correct_enc_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN encoding_correct.enc_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE lst_presta_new_offres;
CREATE TABLE lst_presta_new_offres (offre CHARACTER VARYING(100), nombre_client INTEGER);
DROP TABLE lst_presta_offres;
CREATE TABLE lst_presta_offres (offre CHARACTER VARYING(100), jan_2024 INTEGER, fev_2024 INTEGER, mars_2024 INTEGER, avr_2024 INTEGER, mai_2024 INTEGER, juin_2024 INTEGER, juillet_2024 INTEGER, aout_2024 INTEGER, sept_2024 INTEGER, oct_2024 INTEGER, nov_2024 INTEGER, dec_2024 INTEGER, jan_2025 INTEGER, fev_2025 INTEGER, mars_2025 INTEGER, avr_2025 INTEGER, mai_2025 INTEGER, juin_2025 INTEGER, juillet_2025 INTEGER, aout_2025 INTEGER, sept_2025 INTEGER, oct_2025 INTEGER, nov_2025 INTEGER, dec_2025 INTEGER, jan_2026 INTEGER, fev_2026 INTEGER, mars_2026 INTEGER, avr_2026 INTEGER, mai_2026 INTEGER, juin_2026 INTEGER, juillet_2026 INTEGER, aout_2026 INTEGER, sept_2026 INTEGER, oct_2026 INTEGER, nov_2026 INTEGER, dec_2026 INTEGER);
DROP TABLE lst_presta_recap_detail;
CREATE TABLE lst_presta_recap_detail (offre CHARACTER VARYING(30), august_2025 INTEGER, september_2025 INTEGER, october_2025 INTEGER, november_2025 INTEGER, december_2025 INTEGER, january_2026 INTEGER, evol_mensuel INTEGER, evol_mensuel_pct CHARACTER VARYING(10));
DROP TABLE lst_presta_recap_graph_details;
CREATE TABLE lst_presta_recap_graph_details (offre CHARACTER VARYING(30), february_2025 INTEGER, march_2025 INTEGER, april_2025 INTEGER, may_2025 INTEGER, june_2025 INTEGER, july_2025 INTEGER, august_2025 INTEGER, september_2025 INTEGER, october_2025 INTEGER, november_2025 INTEGER, december_2025 INTEGER, january_2026 INTEGER);
DROP TABLE lst_presta_recap_graph_total;
CREATE TABLE lst_presta_recap_graph_total (offre CHARACTER VARYING(30), february_2025 INTEGER, march_2025 INTEGER, april_2025 INTEGER, may_2025 INTEGER, june_2025 INTEGER, july_2025 INTEGER, august_2025 INTEGER, september_2025 INTEGER, october_2025 INTEGER, november_2025 INTEGER, december_2025 INTEGER, january_2026 INTEGER);
DROP TABLE lst_presta_recap_total;
CREATE TABLE lst_presta_recap_total (offre CHARACTER VARYING(30), august_2025 INTEGER, september_2025 INTEGER, october_2025 INTEGER, november_2025 INTEGER, december_2025 INTEGER, january_2026 INTEGER, evol_mensuel INTEGER, evol_mensuel_pct CHARACTER VARYING(10));
DROP TABLE lst_presta_techno;
CREATE TABLE lst_presta_techno (techno CHARACTER VARYING(30), jan_2025 INTEGER, fev_2025 INTEGER, mars_2025 INTEGER, avr_2025 INTEGER, mai_2025 INTEGER, juin_2025 INTEGER, juillet_2025 INTEGER, aout_2025 INTEGER, sept_2025 INTEGER, oct_2025 INTEGER, nov_2025 INTEGER, dec_2025 INTEGER, mois_courant INTEGER, jan_2026 INTEGER, fev_2026 INTEGER, mars_2026 INTEGER, avr_2026 INTEGER, mai_2026 INTEGER, juin_2026 INTEGER, juillet_2026 INTEGER, aout_2026 INTEGER, sept_2026 INTEGER, oct_2026 INTEGER, nov_2026 INTEGER, dec_2026 INTEGER);
DROP TABLE lst_vlan_usage;
CREATE TABLE lst_vlan_usage (vlan CHARACTER VARYING, usage CHARACTER VARYING);
DROP TABLE t_application_configs;
CREATE TABLE t_application_configs (apcf_id BIGINT DEFAULT nextval('t_application_configs_apcf_id_seq'::regclass) NOT NULL, apcf_component_name CHARACTER VARYING(50), apcf_release CHARACTER(12), apcf_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_application_parameter_values;
CREATE TABLE t_application_parameter_values (appv_id BIGINT DEFAULT nextval('t_application_parameter_values_appv_id_seq'::regclass) NOT NULL, appv_position INTEGER, appv_value CHARACTER VARYING(255), appa_id BIGINT, appv_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_application_parameters;
CREATE TABLE t_application_parameters (appa_id BIGINT DEFAULT nextval('t_application_parameters_appa_id_seq'::regclass) NOT NULL, appa_name CHARACTER(1), appa_remarks CHARACTER VARYING(50), appa_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_atm_profiles;
CREATE TABLE t_atm_profiles (atpr_id BIGINT DEFAULT nextval('t_atm_profiles_atpr_id_seq'::regclass) NOT NULL, atpr_name CHARACTER VARYING(50), thro_id BIGINT, atpr_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_bays;
CREATE TABLE t_bays (bay_id BIGINT DEFAULT nextval('t_bays_bay_id_seq'::regclass) NOT NULL, bay_num SMALLINT NOT NULL, row_id BIGINT, bay_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_card_models;
CREATE TABLE t_card_models (cmod_id BIGINT DEFAULT nextval('t_card_models_cmod_id_seq'::regclass) NOT NULL, cmod_name CHARACTER VARYING(24), cmod_long_name CHARACTER VARYING(70), cmod_type CHARACTER VARYING(1), cmod_ean_code CHARACTER(13), cmod_port_size SMALLINT, cmod_family_name CHARACTER VARYING(4), cmod_remarks CHARACTER VARYING(255), manf_id BIGINT, cmod_version INTEGER DEFAULT 1 NOT NULL, cmod_melt BOOLEAN DEFAULT false);
DROP TABLE t_card_national_profiles;
CREATE TABLE t_card_national_profiles (cnpr_id BIGINT DEFAULT nextval('t_card_national_profiles_cnpr_id_seq'::regclass) NOT NULL, cnpr_group_max_size SMALLINT, cnpr_group_first_position SMALLINT, cnpr_group_adjacent_port SMALLINT, cnpr_group_type CHARACTER(1), cnpr_nb_of_range SMALLINT, cnpr_rareness SMALLINT, cnpr_is_adsl SMALLINT, cnpr_port_number SMALLINT, cnpr_tst_size SMALLINT, cnpr_tt_size SMALLINT, cnpr_gel SMALLINT, csfv_id BIGINT, cnpr_version INTEGER DEFAULT 1 NOT NULL, cnpr_exception BOOLEAN DEFAULT false);
DROP TABLE t_card_soft_vers;
CREATE TABLE t_card_soft_vers (csfv_id BIGINT DEFAULT nextval('t_card_soft_vers_csfv_id_seq'::regclass) NOT NULL, csfv_name CHARACTER VARYING(20), cmod_id BIGINT, csfv_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_cardmodels_sfp;
CREATE TABLE t_cardmodels_sfp (csfp_id BIGINT DEFAULT nextval('t_cardmodels_sfp_csfp_id_seq'::regclass) NOT NULL, cmod_id BIGINT NOT NULL, csfp_typesfp CHARACTER VARYING(20), csfp_portmin INTEGER NOT NULL, csfp_portmax INTEGER NOT NULL, csfp_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_cards;
CREATE TABLE t_cards (card_id BIGINT DEFAULT nextval('t_cards_card_id_seq'::regclass) NOT NULL, card_runtime_type CHARACTER(1), card_num SMALLINT NOT NULL, card_remarks CHARACTER VARYING(128), card_prod_status CHARACTER(1), card_nature CHARACTER(1), cmod_id BIGINT, csfv_id BIGINT, node_id BIGINT, slot_id BIGINT, eqpt_id_delocalized INTEGER, card_version INTEGER DEFAULT 1 NOT NULL, card_creation_time TIMESTAMP(6) WITH TIME ZONE, card_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_d_booked_ports;
CREATE TABLE t_d_booked_ports (port_id BIGINT DEFAULT nextval('t_d_booked_ports_port_id_seq'::regclass) NOT NULL, book_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_d_controlable_rscs;
CREATE TABLE t_d_controlable_rscs (ctrs_type CHARACTER(1), ctrs_role SMALLINT, ctrs_prod_status SMALLINT, ctrs_full_occupied_status CHARACTER(1), ctrs_curr_threshold INTEGER, ctrs_stock_size INTEGER, ctrs_occupied_count INTEGER, ctrs_operator_size SMALLINT, ctrs_vpia INTEGER, ctrs_need_new_vc SMALLINT, rpct_id BIGINT, a_eqpt_id BIGINT, b_eqpt_id BIGINT, a_port_id BIGINT, ctrs_used_count INTEGER, ctrs_version INTEGER DEFAULT 1 NOT NULL, ctrs_creation_time TIMESTAMP(6) WITH TIME ZONE, ctrs_last_modification_time TIMESTAMP(6) WITH TIME ZONE, ctrs_id BIGINT DEFAULT nextval('t_d_controlable_rscs_ctrs_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_d_controlable_rscs.ctrs_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_d_dslam_logical_shelfs;
CREATE TABLE t_d_dslam_logical_shelfs (dsls_prod_status CHARACTER(1), dsls_toc_max SMALLINT, dsls_mutation CHARACTER(1), dsls_updated SMALLINT, dsls_total_port_count SMALLINT, dsls_total_used_port_count SMALLINT, dsls_mnl_available_port_count SMALLINT, dsls_auto_available_port_count SMALLINT, shlf_id BIGINT, eqpt_id BIGINT, dslam_eqpt_id BIGINT, node_id BIGINT, dsls_version INTEGER DEFAULT 1 NOT NULL, dsls_id BIGINT DEFAULT nextval('t_d_dslam_logical_shelfs_dsls_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_d_dslam_logical_shelfs.dsls_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_d_dslam_manelems;
CREATE TABLE t_d_dslam_manelems (dsme_dslam_status CHARACTER(1), dsme_prod_status CHARACTER(1), dsme_updated SMALLINT, dsme_total_port_count INTEGER, dsme_total_used_port_count INTEGER, dsme_mnl_available_port_count INTEGER, dsme_auto_available_port_count INTEGER, dsme_manelem_load INTEGER, dsme_rare_res_count SMALLINT, eqpt_id BIGINT, dslam_eqpt_id BIGINT, master_dslam_eqpt_id BIGINT, source_dslam_eqpt_id BIGINT, node_id BIGINT, dsme_version INTEGER DEFAULT 1 NOT NULL, dsme_id BIGINT DEFAULT nextval('t_d_dslam_manelems_dsme_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_d_dslam_manelems.dsme_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_d_dslam_xdsl_cards;
CREATE TABLE t_d_dslam_xdsl_cards (dxcd_prod_status CHARACTER(1), dxcd_total_port_count SMALLINT, dxcd_total_used_port_count SMALLINT, dxcd_mnl_available_port_count SMALLINT, dxcd_auto_available_port_count SMALLINT, dxcd_is_adsl SMALLINT, dxcd_rareness SMALLINT, dxcd_matrix CHARACTER(1), card_id BIGINT, eqpt_id BIGINT, dslam_eqpt_id BIGINT, shlf_id BIGINT, node_id BIGINT, csfv_id BIGINT, dxcd_version INTEGER DEFAULT 1 NOT NULL, dxcd_id BIGINT DEFAULT nextval('t_d_dslam_xdsl_cards_dxcd_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_d_dslam_xdsl_cards.dxcd_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_d_need_new_vcs;
CREATE TABLE t_d_need_new_vcs (rpct_id BIGINT DEFAULT nextval('t_d_need_new_vcs_rpct_id_seq'::regclass) NOT NULL, rpct_version INTEGER DEFAULT 1 NOT NULL, rvcv_id BIGINT DEFAULT nextval('t_d_need_new_vcs_rvcv_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_d_need_new_vcs.rvcv_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_d_rsc_dslam_tsfs;
CREATE TABLE t_d_rsc_dslam_tsfs (rscd_priority INTEGER, rscd_saturated_nip CHARACTER(1), rscd_nip_type INTEGER, rpct_id BIGINT, dslam_eqpt_id BIGINT, tsft_id BIGINT, nip_eqpt_id BIGINT, rscd_version INTEGER DEFAULT 1 NOT NULL, rscd_id BIGINT DEFAULT nextval('t_d_rsc_dslam_tsfs_rscd_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_d_rsc_dslam_tsfs.rscd_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_d_rsc_vcis;
CREATE TABLE t_d_rsc_vcis (rscv_vci BIGINT DEFAULT nextval('t_d_rsc_vcis_rscv_vci_seq'::regclass) NOT NULL, rscv_status CHARACTER(1), rpct_id BIGINT, rscv_version INTEGER DEFAULT 1 NOT NULL, rscv_creation_time TIMESTAMP(6) WITH TIME ZONE, rscv_last_modification_time TIMESTAMP(6) WITH TIME ZONE, rscv_id BIGINT DEFAULT nextval('t_d_rsc_vcis_rscv_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_d_rsc_vcis.rscv_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_d_xdsl_card_stripes;
CREATE TABLE t_d_xdsl_card_stripes (xdcs_port_count SMALLINT, xdcs_module CHARACTER(1), xdcs_up_range SMALLINT, xdcs_down_range SMALLINT, xdcs_up_level INTEGER, xdcs_down_level INTEGER, card_id BIGINT, strp_id BIGINT, eqpt_id BIGINT, xdcs_version INTEGER DEFAULT 1 NOT NULL, xdcs_id BIGINT DEFAULT nextval('t_d_xdsl_card_stripes_xdcs_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_d_xdsl_card_stripes.xdcs_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_distributors;
CREATE TABLE t_distributors (dist_id BIGINT DEFAULT nextval('t_distributors_dist_id_seq'::regclass) NOT NULL, node_id BIGINT, dist_prod_orientation INTEGER NOT NULL, dist_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_dr;
CREATE TABLE t_dr (dr_code CHARACTER VARYING(3) NOT NULL, dr_name CHARACTER VARYING(30) NOT NULL, dr_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_dslam_access_constraints;
CREATE TABLE t_dslam_access_constraints (dsac_id BIGINT DEFAULT nextval('t_dslam_access_constraints_dsac_id_seq'::regclass) NOT NULL, dsac_constraint_type CHARACTER VARYING(10), dsag_constraint_title CHARACTER VARYING(20), dsac_priority INTEGER, dsac_dslam CHARACTER VARYING(8), dsac_shelf_num SMALLINT, dsac_card_num SMALLINT, dsac_port_num SMALLINT, dsac_port_group_name CHARACTER VARYING(3), dsac_stripe_name CHARACTER VARYING(6), dsac_pin_num SMALLINT, dsac_module CHARACTER VARYING(1), dsac_change_module SMALLINT, dsac_serial_num_ont CHARACTER VARYING(13), dsac_password CHARACTER VARYING(10), dsac_matrix CHARACTER(1), dsag_id BIGINT, dsac_version INTEGER DEFAULT 1 NOT NULL, dsac_creation_time TIMESTAMP(6) WITH TIME ZONE, dsac_last_modification_time TIMESTAMP(6) WITH TIME ZONE, dsac_old_serial_num_ont CHARACTER VARYING(13));
DROP TABLE t_dslam_assignments;
CREATE TABLE t_dslam_assignments (dsag_id BIGINT DEFAULT nextval('t_dslam_assignments_dsag_id_seq'::regclass) NOT NULL, dsag_techno_name CHARACTER VARYING(20), dsag_pin_count SMALLINT, dsag_module CHARACTER VARYING(1), dsag_up_range SMALLINT, dsag_down_range SMALLINT, dsag_up_level SMALLINT, dsag_down_level SMALLINT, dsag_constraint_size SMALLINT, mkfl_id BIGINT, dsag_version INTEGER DEFAULT 1 NOT NULL, dsag_creation_time TIMESTAMP(6) WITH TIME ZONE, dsag_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_dslam_soft_vers;
CREATE TABLE t_dslam_soft_vers (dssv_id BIGINT DEFAULT nextval('t_dslam_soft_vers_dssv_id_seq'::regclass) NOT NULL, dssv_name CHARACTER VARYING(20), lgem_id BIGINT, dssv_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_epc_order_lines;
CREATE TABLE t_epc_order_lines (epco_id BIGINT DEFAULT nextval('t_epc_order_lines_epco_id_seq'::regclass) NOT NULL, epco_epc_id CHARACTER VARYING(20) NOT NULL, epco_update_mode CHARACTER VARYING(1) NOT NULL, epco_nd_service CHARACTER VARYING(20), epco_main_epc_id CHARACTER VARYING(20), epco_order_line_num SMALLINT, epco_marketed_service CHARACTER VARYING(255), epco_reselled_offer SMALLINT, epco_marketed_interface CHARACTER VARYING(20), epco_marketed_rate CHARACTER VARYING(30), epco_operator CHARACTER VARYING(40), epco_server_constraint_size SMALLINT, epco_tr_assignment_size SMALLINT, mkfl_id BIGINT, epco_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_epc_vers;
CREATE TABLE t_epc_vers (epcv_id BIGINT DEFAULT nextval('t_epc_vers_epcv_id_seq'::regclass) NOT NULL, epcv_vers_num SMALLINT NOT NULL, epcv_current_state CHARACTER VARYING(1) NOT NULL, epcv_last_modifydate_date DATE NOT NULL, epcv_last_modifydate_time INTEGER, mrtd_id BIGINT, epc_id BIGINT, tcsv_id BIGINT, epcv_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_epc_vers_comps;
CREATE TABLE t_epc_vers_comps (epvc_id BIGINT DEFAULT nextval('t_epc_vers_comps_epvc_id_seq'::regclass) NOT NULL, epvc_vers_num NUMERIC(10,0), stco_id BIGINT, epcv_id BIGINT, mrsv_id BIGINT, mrdv_id BIGINT, epvc_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_epc_vers_impacts;
CREATE TABLE t_epc_vers_impacts (evim_id BIGINT DEFAULT nextval('t_epc_vers_impacts_evim_id_seq'::regclass) NOT NULL, evim_impact_type SMALLINT, evim_mandatory SMALLINT, epcv_id BIGINT, mkfl_id BIGINT, evim_version INTEGER DEFAULT 1 NOT NULL, evim_creation_time TIMESTAMP(6) WITH TIME ZONE, evim_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_epcs;
CREATE TABLE t_epcs (epc_id BIGINT DEFAULT nextval('t_epcs_epc_id_seq'::regclass) NOT NULL, epc_epc_id CHARACTER VARYING(20) NOT NULL, epc_old_id_epc CHARACTER VARYING(20), epc_main_epc_id CHARACTER VARYING(20), epc_opendate_date DATE, epc_opendate_time INTEGER, epc_nd_service CHARACTER VARYING(20), epc_remarks CHARACTER VARYING(50), epc_reselled_offer SMALLINT NOT NULL, epc_vers_num_0 SMALLINT, epc_vers_num_1 SMALLINT, epc_vers_0 CHARACTER VARYING(37), epc_vers_1 CHARACTER VARYING(37), epc_ordre SMALLINT, epc_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_eqpt_shf_mdl_compatibilities;
CREATE TABLE t_eqpt_shf_mdl_compatibilities (esmc_id BIGINT DEFAULT nextval('t_eqpt_shf_mdl_compatibilities_esmc_id_seq'::regclass) NOT NULL, shmd_id BIGINT, lgem_id BIGINT, esmc_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_equipments;
CREATE TABLE t_equipments (eqpt_id BIGINT DEFAULT nextval('t_equipments_eqpt_id_seq'::regclass) NOT NULL, eqpt_runtime_type SMALLINT, eqpt_name CHARACTER VARYING(20) NOT NULL, eqpt_ip_address CHARACTER VARYING(39), eqpt_remarks CHARACTER VARYING(255), eqpt_owner CHARACTER VARYING(20), eqpt_saturation_status CHARACTER VARYING(1), eqpt_status CHARACTER VARYING(1), eqpt_rank SMALLINT, eqpt_toc_max_init SMALLINT, eqpt_prod_status CHARACTER(1), eqpt_load INTEGER, eqpt_renaming_done SMALLINT, eqpt_hub_code CHARACTER VARYING(19), eqpt_communication_port INTEGER, lgem_id BIGINT, node_id BIGINT, manager_eqpt_id BIGINT, dssv_id BIGINT, master_eqpt_id BIGINT, source_eqpt_id BIGINT, manf_id BIGINT, eqpt_id_real_dslam INTEGER, node_id_delocalized INTEGER, epqt_version INTEGER DEFAULT 1 NOT NULL, eqpt_creation_time TIMESTAMP(6) WITH TIME ZONE, eqpt_last_modification_time TIMESTAMP(6) WITH TIME ZONE, eqpt_date_mise_en_service TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_es;
CREATE TABLE t_es (es_id BIGINT DEFAULT nextval('t_es_es_id_seq'::regclass) NOT NULL, es_request_date DATE, es_request_time INTEGER, es_end_date DATE, es_end_time INTEGER, es_status SMALLINT, es_equipment CHARACTER VARYING(255), es_user CHARACTER VARYING(255), es_message CHARACTER(255), es_code SMALLINT, es_file_name CHARACTER(255), es_input_file TEXT, est_id BIGINT, es_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_es_connexions;
CREATE TABLE t_es_connexions (esc_id BIGINT DEFAULT nextval('t_es_connexions_esc_id_seq'::regclass) NOT NULL, esc_platform_ip CHARACTER VARYING(100), esc_user CHARACTER VARYING(20), esc_password CHARACTER VARYING(100), esc_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_es_habilitations;
CREATE TABLE t_es_habilitations (esh_id BIGINT DEFAULT nextval('t_es_habilitations_esh_id_seq'::regclass) NOT NULL, esh_role CHARACTER VARYING(50), esh_droit CHARACTER(1), est_id BIGINT, esh_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_es_logs;
CREATE TABLE t_es_logs (esl_id BIGINT DEFAULT nextval('t_es_logs_esl_id_seq'::regclass) NOT NULL, esl_file_name CHARACTER VARYING(255), esl_type SMALLINT, esl_log_file TEXT, es_id BIGINT, esl_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_es_types;
CREATE TABLE t_es_types (est_id BIGINT DEFAULT nextval('t_es_types_est_id_seq'::regclass) NOT NULL, est_name CHARACTER VARYING(100), est_script_dir CHARACTER VARYING(255), est_file_name CHARACTER VARYING(255), est_log_dir CHARACTER VARYING(255), est_log_name CHARACTER VARYING(255), est_report_dir CHARACTER VARYING(255), est_report_name CHARACTER VARYING(255), est_arguments CHARACTER VARYING(255), est_description CHARACTER VARYING(255), est_input_files_count INTEGER, esc_id BIGINT, est_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_ftth_lock_onts;
CREATE TABLE t_ftth_lock_onts (flko_id BIGINT DEFAULT nextval('t_ftth_lock_onts_flko_id_seq'::regclass) NOT NULL, flko_ont_num INTEGER, port_id BIGINT, flko_version INTEGER DEFAULT 1 NOT NULL, CONSTRAINT unique_port_ont UNIQUE (flko_ont_num, port_id));
DROP TABLE t_function_codes;
CREATE TABLE t_function_codes (fctc_id BIGINT DEFAULT nextval('t_function_codes_fctc_id_seq'::regclass) NOT NULL, fctc_name CHARACTER VARYING(6), fctc_type SMALLINT, fctc_version INTEGER DEFAULT 1 NOT NULL, fctc_techno_name CHARACTER VARYING(5));
COMMENT ON COLUMN t_function_codes.fctc_techno_name IS 'G09R04C07 - Jira 943 - Evol GMK';
DROP TABLE t_group_localisation;
CREATE TABLE t_group_localisation (group_localisation_id BIGINT DEFAULT nextval('t_group_localisation_group_localisation_id_seq'::regclass) NOT NULL, group_name CHARACTER VARYING(15) NOT NULL, group_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_icc_updates;
CREATE TABLE t_icc_updates (iccu_id BIGINT DEFAULT nextval('t_icc_updates_iccu_id_seq'::regclass) NOT NULL, iccu_logical_shelf_num SMALLINT, iccu_dslam_name CHARACTER VARYING(12), eqpt_id BIGINT, iccu_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_interfaces;
CREATE TABLE t_interfaces (intf_id BIGINT DEFAULT nextval('t_interfaces_intf_id_seq'::regclass) NOT NULL, intf_name CHARACTER VARYING(20), intf_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_line_profiles;
CREATE TABLE t_line_profiles (lnpr_id BIGINT DEFAULT nextval('t_line_profiles_lnpr_id_seq'::regclass) NOT NULL, lnpr_name CHARACTER VARYING(50), lnpr_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_link_dr_group_localisation;
CREATE TABLE t_link_dr_group_localisation (group_localisation_id BIGINT NOT NULL, dr_code CHARACTER VARYING(3) NOT NULL, ldgl_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_local_areas;
CREATE TABLE t_local_areas (loca_id BIGINT NOT NULL, loca_local_area_short_name CHARACTER VARYING(8), loca_local_area_long_name CHARACTER VARYING(15), loca_version INTEGER DEFAULT 1 NOT NULL, loca_creation_date DATE, loca_creation_time INTEGER, loca_last_modification_date DATE, loca_last_modification_time INTEGER);
DROP TABLE t_logical_eqpt_models;
CREATE TABLE t_logical_eqpt_models (lgem_id BIGINT DEFAULT nextval('t_logical_eqpt_models_lgem_id_seq'::regclass) NOT NULL, lgem_name CHARACTER VARYING(16), lgem_type CHARACTER VARYING(3), lgem_real_name CHARACTER VARYING(70), manf_id BIGINT, lgem_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_making_files;
CREATE TABLE t_making_files (mkfl_id BIGINT DEFAULT nextval('t_making_files_mkfl_id_seq'::regclass) NOT NULL, mkfl_file_id CHARACTER VARYING(20) NOT NULL, mkfl_customer_name CHARACTER VARYING(32) NOT NULL, mkfl_customer_id CHARACTER VARYING(20), mkfl_nd CHARACTER VARYING(15), mkfl_business_process SMALLINT NOT NULL, mkfl_current_crc_id CHARACTER VARYING(24), mkfl_previous_crc_id CHARACTER VARYING(24), mkfl_base_code_42c CHARACTER VARYING(6) NOT NULL, mkfl_center_code_42c CHARACTER VARYING(3) NOT NULL, mkfl_creation_date_date DATE, mkfl_creation_date_time INTEGER NOT NULL, mkfl_status SMALLINT, mkfl_is_compatible SMALLINT, mkfl_backtrack SMALLINT, mkfl_process_g3 CHARACTER VARYING(1), mkfl_config_direction_g3 CHARACTER VARYING(1), mkfl_port_change SMALLINT, mkfl_reseller_offer SMALLINT, mkfl_dslam_assignment_size SMALLINT, mkfl_epc_impact_size SMALLINT, mkfl_epc_order_line_size SMALLINT, mkfl_mrt_impact_size SMALLINT, mkfl_far_id CHARACTER VARYING(12), mkfl_last_config_phase CHARACTER VARYING(6), oper_id BIGINT, mkfl_version INTEGER DEFAULT 1 NOT NULL, mkfl_last_modification_time TIMESTAMP(6) WITH TIME ZONE, mkfl_sender_id CHARACTER VARYING(4));
COMMENT ON COLUMN t_making_files.mkfl_business_process IS 'CL = 0 / C/L
SAV = 1 / SAV
AVP = 2 / AVP
RES = 3 / Réorganisation Réseau
DLM = 4 / DLM
DLM_OFFER = 5 / DLM Offer';
COMMENT ON COLUMN t_making_files.mkfl_sender_id IS 'G09R06C00 - Jira 6737 - Discerner les differents process xDSL';
DROP TABLE t_manufacturers;
CREATE TABLE t_manufacturers (manf_id BIGINT DEFAULT nextval('t_manufacturers_manf_id_seq'::regclass) NOT NULL, manf_name CHARACTER VARYING(20), manf_short_name CHARACTER VARYING(3), manf_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_media_links;
CREATE TABLE t_media_links (mdlk_id BIGINT DEFAULT nextval('t_media_links_mdlk_id_seq'::regclass) NOT NULL, mdlk_point_a_phys_end_type CHARACTER(1), mdlk_point_b_ce_card_num SMALLINT, mdlk_point_b_ce_port_num SMALLINT, mdlk_point_b_ce_shelf_num SMALLINT, mdlk_point_b_cust_eqpt_info CHARACTER VARYING(8), mdlk_point_b_phys_end_type CHARACTER(1), mdlk_remarks CHARACTER VARYING(240), mdlk_update_date DATE, mdlk_update_time INTEGER, mdlk_lag_num CHARACTER VARYING(4), mdlk_master CHARACTER(1), mdlk_status SMALLINT, mdlk_origin CHARACTER VARYING(2), mdlk_rank SMALLINT, mdlk_serial_num CHARACTER VARYING(4) NOT NULL, mdlk_migration_infos CHARACTER VARYING(80), a_eqpt_id BIGINT, b_eqpt_id BIGINT, a_node_id BIGINT, b_node_id BIGINT, a_port_id BIGINT, b_port_id BIGINT, ce_eqpt_id BIGINT, fctc_id BIGINT, mdlk_version INTEGER DEFAULT 1 NOT NULL, mdlk_creation_time TIMESTAMP(6) WITH TIME ZONE, mdlk_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_mrt_access_dslam_vers;
CREATE TABLE t_mrt_access_dslam_vers (mrdv_id BIGINT DEFAULT nextval('t_mrt_access_dslam_vers_mrdv_id_seq'::regclass) NOT NULL, mrdv_interleave CHARACTER VARYING(1) NOT NULL, mrdv_intsiamg3offer CHARACTER VARYING(50) NOT NULL, mrdv_current_state CHARACTER VARYING(1) NOT NULL, mrdv_serial_ont_num CHARACTER VARYING(13), mrdv_vers_num SMALLINT, mrdv_password CHARACTER VARYING(10), mrdv_last_state_date DATE, mrdv_last_state_time INTEGER, ontp_id BIGINT, mrdv_runtime_type CHARACTER(1), lnpr_id BIGINT, mrtd_id BIGINT, mrdv_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_mrt_access_dslams;
CREATE TABLE t_mrt_access_dslams (mrtd_id BIGINT DEFAULT nextval('t_mrt_access_dslams_mrtd_id_seq'::regclass) NOT NULL, mrtd_customer_id CHARACTER VARYING(20) NOT NULL, mrtd_nd CHARACTER VARYING(15) NOT NULL, mrtd_customer_name CHARACTER VARYING(32), mrtd_crc_mrt_id CHARACTER VARYING(24) NOT NULL, mrtd_farid CHARACTER VARYING(12), mrtd_crc_mrt_date DATE, mrtd_crc_mrt_time INTEGER, mrtd_autodetect SMALLINT, mrtd_vers_num_0 SMALLINT, mrtd_vers_num_1 SMALLINT, mrtd_point_a_interface_id CHARACTER VARYING(255), mrtd_point_a_phys_end_type CHARACTER(1), mrtd_interface_type CHARACTER(1), mrtd_update_date DATE, mrtd_update_time INTEGER, oper_id BIGINT, tcty_id BIGINT, a_eqpt_id BIGINT, a_node_id BIGINT, a_port_id BIGINT, mrty_id BIGINT, a_pogr_id BIGINT, mrtd_info_portgp_tmp CHARACTER VARYING(255), mrtd_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_mrt_access_msan_usage;
CREATE TABLE t_mrt_access_msan_usage (mrmu_id BIGINT DEFAULT nextval('t_mrt_access_msan_usage_mrmu_id_seq'::regclass) NOT NULL, mrdv_id BIGINT NOT NULL, mrmu_hasinternet BOOLEAN NOT NULL, mrmu_hastv BOOLEAN NOT NULL, mrmu_hastoip BOOLEAN NOT NULL, mrmu_last_modification_time TIMESTAMP(6) WITHOUT TIME ZONE, mrmu_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_mrt_access_service_vers;
CREATE TABLE t_mrt_access_service_vers (mrsv_id BIGINT DEFAULT nextval('t_mrt_access_service_vers_mrsv_id_seq'::regclass) NOT NULL, mrsv_current_state CHARACTER VARYING(1) NOT NULL, mrsv_last_state_date DATE NOT NULL, mrsv_last_state_time INTEGER, mrsv_vers_num SMALLINT NOT NULL, mrsv_runtime_type CHARACTER(1), atpr_id BIGINT, mras_id BIGINT, srpr_id BIGINT, mrsv_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_mrt_access_services;
CREATE TABLE t_mrt_access_services (mras_id BIGINT DEFAULT nextval('t_mrt_access_services_mras_id_seq'::regclass) NOT NULL, mras_circuit_id CHARACTER VARYING(40), mras_remote_id CHARACTER VARYING(15), mras_utilisation SMALLINT, mras_vers_num_0 SMALLINT, mras_vers_num_1 SMALLINT, mras_saved_operator CHARACTER VARYING(11), mrty_id BIGINT, oper_id BIGINT, eqpt_id BIGINT, a_node_id BIGINT, mras_version INTEGER DEFAULT 1 NOT NULL, mras_creation_time TIMESTAMP(6) WITH TIME ZONE, mras_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_mrt_types;
CREATE TABLE t_mrt_types (mrty_id BIGINT DEFAULT nextval('t_mrt_types_mrty_id_seq'::regclass) NOT NULL, mrty_name CHARACTER VARYING(40), mrty_short_name CHARACTER VARYING(16), mrty_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_mrt_vers_impacts;
CREATE TABLE t_mrt_vers_impacts (mrvi_id BIGINT DEFAULT nextval('t_mrt_vers_impacts_mrvi_id_seq'::regclass) NOT NULL, mrvi_initial_status CHARACTER(1) NOT NULL, mrvi_current_status CHARACTER(1) NOT NULL, mrvi_target_status CHARACTER(1) NOT NULL, mkfl_id BIGINT, mrsv_id BIGINT, mrdv_id BIGINT, mrvi_version INTEGER DEFAULT 1 NOT NULL, mrvi_creation_time TIMESTAMP(6) WITH TIME ZONE, mrvi_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_mutations_requests;
CREATE TABLE t_mutations_requests (murq_id BIGINT DEFAULT nextval('t_mutations_requests_murq_id_seq'::regclass) NOT NULL, murq_shelf_card_port_n CHARACTER VARYING(255), murq_shelf_card_port_n1 CHARACTER VARYING(255), murq_shelf_card_port_n1_source CHARACTER VARYING(255), murq_shelf_card_port_n_source CHARACTER VARYING(255), murq_hub_code CHARACTER VARYING(19), murq_creation_date DATE, murq_creation_time INTEGER, murq_execution_date DATE, murq_execution_time INTEGER, murq_equipment_n CHARACTER VARYING(10), murq_equipment_n1 CHARACTER VARYING(10), murq_equipment_n1_source CHARACTER VARYING(10), murq_equipment_n_source CHARACTER VARYING(10), murq_status CHARACTER VARYING(255), murq_request_status CHARACTER VARYING(255), murq_node_n CHARACTER VARYING(25), murq_node_n1 CHARACTER VARYING(25), murq_node_n1_source CHARACTER VARYING(25), murq_node_n_source CHARACTER VARYING(25), murq_new_dslam_name CHARACTER VARYING(10), murq_renaming CHARACTER VARYING(255), murq_execution_type CHARACTER(1), murq_new_fct_code CHARACTER VARYING(10), murq_new_serial_num SMALLINT, murq_version INTEGER DEFAULT 1 NOT NULL, murq_old_lag_number CHARACTER VARYING(4), murq_new_lag_number CHARACTER VARYING(4), murq_bloc_demandes INTEGER, murq_file BYTEA, murq_nip_gp CHARACTER VARYING(8), murq_nip_emw CHARACTER VARYING(8), murq_nip_tvnum CHARACTER VARYING(8), murq_nip_bng CHARACTER VARYING(8), murq_origin CHARACTER VARYING(3));
COMMENT ON COLUMN t_mutations_requests.murq_file IS 'G09R06C02 - Jira BRA-7122 - Contrôle de mutation en asynchrone';
DROP TABLE t_net_port_models;
CREATE TABLE t_net_port_models (npmd_id BIGINT DEFAULT nextval('t_net_port_models_npmd_id_seq'::regclass) NOT NULL, npmd_port_type CHARACTER VARYING(10), npmd_port_size SMALLINT, npmd_port_init SMALLINT, cmod_id BIGINT, npmd_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_net_resource_rels;
CREATE TABLE t_net_resource_rels (nrre_id BIGINT DEFAULT nextval('t_net_resource_rels_nrre_id_seq'::regclass) NOT NULL, oper_id BIGINT, rpct_id BIGINT, nrre_version INTEGER DEFAULT 1 NOT NULL, nrre_creation_time TIMESTAMP(6) WITH TIME ZONE, nrre_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_nip_server_assocs;
CREATE TABLE t_nip_server_assocs (nsra_id BIGINT DEFAULT nextval('t_nip_server_assocs_nsra_id_seq'::regclass) NOT NULL, eqpt_id BIGINT, serv_id BIGINT, tst_id BIGINT, nsra_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_no_back_on_technos;
CREATE TABLE t_no_back_on_technos (nbkt_id BIGINT DEFAULT nextval('t_no_back_on_technos_nbkt_id_seq'::regclass) NOT NULL, tcty_id BIGINT, dist_id BIGINT, node_id BIGINT, nbkt_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_nodes;
CREATE TABLE t_nodes (node_id BIGINT DEFAULT nextval('t_nodes_node_id_seq'::regclass) NOT NULL, node_node_code CHARACTER VARYING(6), node_base_code42c CHARACTER VARYING(6), node_gestion_code_group CHARACTER VARYING(3), node_center_code42c CHARACTER VARYING(3), node_dr_code CHARACTER VARYING(3), node_name42c CHARACTER VARYING(20), node_function_code CHARACTER VARYING(4), node_international_name CHARACTER VARYING(19), node_nra_type CHARACTER VARYING(1), site_id BIGINT, node_version INTEGER DEFAULT 1 NOT NULL, node_creation_date DATE, node_creation_time INTEGER, node_last_modification_date DATE, node_last_modification_time INTEGER);
DROP TABLE t_ont_profiles;
CREATE TABLE t_ont_profiles (ontp_id BIGINT DEFAULT nextval('t_ont_profiles_ontp_id_seq'::regclass) NOT NULL, ontp_card_num SMALLINT, ontp_card_type CHARACTER VARYING(20), ontp_port_num SMALLINT, ontp_port_type CHARACTER VARYING(10), ontp_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_operators;
CREATE TABLE t_operators (oper_id BIGINT DEFAULT nextval('t_operators_oper_id_seq'::regclass) NOT NULL, oper_name CHARACTER VARYING(6), oper_long_name CHARACTER VARYING(24), oper_id_cocpit INTEGER NOT NULL, oper_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_p_intsiam_concat_offers;
CREATE TABLE t_p_intsiam_concat_offers (isco_concat_label CHARACTER VARYING(100), isco_version INTEGER DEFAULT 1 NOT NULL, isco_id BIGINT DEFAULT nextval('t_p_intsiam_concat_offers_isco_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_p_intsiam_concat_offers.isco_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_p_intsiam_offers;
CREATE TABLE t_p_intsiam_offers (iso_libelle_intsiam CHARACTER(50), iso_name_tech_service_concat CHARACTER(50), iso_version INTEGER DEFAULT 1 NOT NULL, iso_id BIGINT DEFAULT nextval('t_p_intsiam_offers_iso_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_p_intsiam_offers.iso_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_p_pcp_repos;
CREATE TABLE t_p_pcp_repos (pcpr_shelf_model_id INTEGER, pcpr_shelf_model_short_name CHARACTER(24), pcpr_slot_model_id INTEGER, pcpr_slot_model_poa CHARACTER(8), pcpr_card_model_id INTEGER, pcpr_card_model_short_name CHARACTER(24), pcpr_pcp_model_id INTEGER, pcpr_pcp_model_name CHARACTER(10), pcpr_pcp_model_poa CHARACTER(8), pcpr_pcp_functionality INTEGER, pcpr_pcp_model_nature INTEGER, pcpr_pcp_frame_id INTEGER, pcpr_pcp_frame_name CHARACTER(10), pcpr_pcp_frame_snw_frame_id INTEGER, pcpr_pcp_located_on_shelf INTEGER, pcpr_pcp_number_on_shelf INTEGER, pcpr_version INTEGER DEFAULT 1 NOT NULL, pcpr_id BIGINT DEFAULT nextval('t_p_pcp_repos_pcpr_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_p_pcp_repos.pcpr_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_p_slot_repos;
CREATE TABLE t_p_slot_repos (sltr_shelf_model_id INTEGER, sltr_shelf_model_short_name CHARACTER(24), sltr_shelf_model_name CHARACTER(70), sltr_slot_model_id INTEGER, sltr_slot_model_name CHARACTER(30), sltr_slot_model_poa CHARACTER(8), sltr_slot_number_on_shelf INTEGER, sltr_version INTEGER DEFAULT 1 NOT NULL, sltr_id BIGINT DEFAULT nextval('t_p_slot_repos_sltr_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_p_slot_repos.sltr_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_p_talia_logical_bays;
CREATE TABLE t_p_talia_logical_bays (tlby_label CHARACTER VARYING(6), tlby_version INTEGER DEFAULT 1 NOT NULL, tlby_id BIGINT DEFAULT nextval('t_p_talia_logical_bays_tlby_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_p_talia_logical_bays.tlby_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_p_talia_service_ids;
CREATE TABLE t_p_talia_service_ids (tsid_ts_component_name CHARACTER VARYING(50), tsid_service_id INTEGER, tsid_version INTEGER DEFAULT 1 NOT NULL, tsid_id BIGINT DEFAULT nextval('t_p_talia_service_ids_tsid_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_p_talia_service_ids.tsid_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_p_tech_service_filters;
CREATE TABLE t_p_tech_service_filters (tsfr_tech_serv_name CHARACTER VARYING(50), tsfr_case_number SMALLINT, tsfr_brasil_g3_label CHARACTER VARYING(50), tsfr_add_on_label CHARACTER VARYING(50), tsfr_version INTEGER DEFAULT 1 NOT NULL, tsfr_id BIGINT DEFAULT nextval('t_p_tech_service_filters_tsfr_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_p_tech_service_filters.tsfr_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_p_tst_to_comp_servs;
CREATE TABLE t_p_tst_to_comp_servs (ttcs_tst_name CHARACTER VARYING(20), ttcs_comp_serv_id SMALLINT, ttcs_specif INTEGER, ttcs_version INTEGER DEFAULT 1 NOT NULL, ttcs_id BIGINT DEFAULT nextval('t_p_tst_to_comp_servs_ttcs_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_p_tst_to_comp_servs.ttcs_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_port_groups;
CREATE TABLE t_port_groups (pogr_id BIGINT DEFAULT nextval('t_port_groups_pogr_id_seq'::regclass) NOT NULL, pogr_name CHARACTER VARYING(3), pogr_group_type CHARACTER VARYING(1), pogr_management_policy CHARACTER VARYING(1), pogr_version INTEGER DEFAULT 1 NOT NULL, pogr_creation_time TIMESTAMP(6) WITH TIME ZONE, pogr_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_ports;
CREATE TABLE t_ports (port_id BIGINT DEFAULT nextval('t_ports_port_id_seq'::regclass) NOT NULL, port_num SMALLINT, port_type CHARACTER(1), port_pin_num SMALLINT, port_out_status CHARACTER VARYING(1) NOT NULL, port_occup_status SMALLINT, port_occup_ont INTEGER, port_occupation_status SMALLINT, port_activation_status SMALLINT, port_prod_status CHARACTER VARYING(1), port_remarks CHARACTER VARYING(255), port_reservation_date DATE, port_logical_occup_cpt SMALLINT, port_quality CHARACTER(1), port_attribuable SMALLINT, card_id BIGINT, prst_id BIGINT, slot_id BIGINT, strp_id BIGINT, tst_id BIGINT, pogr_id BIGINT, port_group_gestion_infos CHARACTER VARYING(24), port_version INTEGER DEFAULT 1 NOT NULL, port_date_plp DATE, port_creation_time TIMESTAMP(6) WITH TIME ZONE, port_last_modification_time TIMESTAMP(6) WITH TIME ZONE, port_nb_ont_max SMALLINT);
DROP TABLE t_prestations;
CREATE TABLE t_prestations (prst_id BIGINT DEFAULT nextval('t_prestations_prst_id_seq'::regclass) NOT NULL, prst_prestation_num CHARACTER VARYING(32), prst_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_res_prod_controlables;
CREATE TABLE t_res_prod_controlables (rpct_id BIGINT DEFAULT nextval('t_res_prod_controlables_rpct_id_seq'::regclass) NOT NULL, rpct_type CHARACTER VARYING(1), rpct_allocated_vc_count INTEGER, rpct_ccl_name CHARACTER VARYING(32), rpct_associated_ccl_name CHARACTER VARYING(32), rpct_prod_status SMALLINT, rpct_prod_thresold INTEGER NOT NULL, rpct_thresold_control SMALLINT NOT NULL, rpct_forwarding_mode SMALLINT, rpct_mode CHARACTER VARYING(1), rpct_vlan_interne CHARACTER VARYING(5), rpct_vc_max INTEGER, rpct_vc_min INTEGER, rpct_point_a_interface_id CHARACTER VARYING(39), rpct_point_a_interface_type CHARACTER VARYING(1), rpct_point_a_phys_end_type CHARACTER VARYING(255), rpct_point_b_ce_card_num SMALLINT, rpct_point_b_ce_port_num SMALLINT, rpct_point_b_ce_shelf_num SMALLINT, rpct_point_b_interface_id CHARACTER VARYING(39), rpct_point_b_interface_type CHARACTER VARYING(1), rpct_point_b_phys_end_type CHARACTER VARYING(255), rpct_remarks CHARACTER VARYING(255), rpct_update_date DATE, rpct_update_time INTEGER, role_id BIGINT, a_eqpt_id BIGINT, a_node_id BIGINT, a_port_id BIGINT, a_pogr_id BIGINT, b_eqpt_id BIGINT, b_node_id BIGINT, b_port_id BIGINT, b_pogr_id BIGINT, ce_eqpt_id BIGINT, mrty_id BIGINT, rpct_version INTEGER DEFAULT 1 NOT NULL, rpct_allocables_vc_count INTEGER, rpct_nb_locked_ranges SMALLINT, rpct_vorgang CHARACTER VARYING(80), rpct_creation_time TIMESTAMP(6) WITH TIME ZONE, rpct_last_modification_time TIMESTAMP(6) WITH TIME ZONE, input_bbc_usage CHARACTER VARYING(50), rpct_prov_status CHARACTER VARYING(3));
DROP TABLE t_res_prod_controlers;
CREATE TABLE t_res_prod_controlers (rpco_id BIGINT DEFAULT nextval('t_res_prod_controlers_rpco_id_seq'::regclass) NOT NULL, eqpt_id BIGINT, tsft_id BIGINT, rpco_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_res_prod_roles;
CREATE TABLE t_res_prod_roles (rpro_id BIGINT DEFAULT nextval('t_res_prod_roles_rpro_id_seq'::regclass) NOT NULL, rpro_priority SMALLINT NOT NULL, rpro_vrf CHARACTER VARYING(4), dslam_eqpt_id BIGINT, nip_eqpt_id BIGINT, tsft_id BIGINT, rpct_id BIGINT, rpco_id BIGINT, rpro_version INTEGER DEFAULT 1 NOT NULL, rpro_creation_time TIMESTAMP(6) WITH TIME ZONE, rpro_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_resource_constraints;
CREATE TABLE t_resource_constraints (rcst_id BIGINT DEFAULT nextval('t_resource_constraints_rcst_id_seq'::regclass) NOT NULL, rcst_constraint_type CHARACTER VARYING(10), rcst_constraint_title CHARACTER VARYING(20), rcst_dslam_rank SMALLINT, rcst_shelf_num SMALLINT, rcst_card_num SMALLINT, rcst_priority SMALLINT, rcst_port_num SMALLINT, rcst_portgroup_name CHARACTER VARYING(3), rcst_interface_type CHARACTER VARYING(1), rcst_interface_id CHARACTER VARYING(39), rcst_ccl_name CHARACTER VARYING(32), tass_id BIGINT, rcst_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_resource_usages;
CREATE TABLE t_resource_usages (rsus_id BIGINT DEFAULT nextval('t_resource_usages_rsus_id_seq'::regclass) NOT NULL, rsus_index INTEGER NOT NULL, rsus_vci INTEGER, rsus_vpi INTEGER, rsus_user_side_vlan INTEGER, rsus_booking_priority INTEGER, rsus_resource_role INTEGER, rpct_id BIGINT, mras_id BIGINT, tr_id BIGINT, mrtd_id BIGINT, rsus_version INTEGER DEFAULT 1 NOT NULL, rsus_creation_time TIMESTAMP(6) WITH TIME ZONE, rsus_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_roles;
CREATE TABLE t_roles (role_id BIGINT DEFAULT nextval('t_roles_role_id_seq'::regclass) NOT NULL, role_name CHARACTER VARYING(24), role_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_rooms;
CREATE TABLE t_rooms (room_id BIGINT DEFAULT nextval('t_rooms_room_id_seq'::regclass) NOT NULL, room_name CHARACTER VARYING(4) NOT NULL, node_id BIGINT, room_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_rows;
CREATE TABLE t_rows (row_id BIGINT DEFAULT nextval('t_rows_row_id_seq'::regclass) NOT NULL, row_num CHARACTER VARYING(3) NOT NULL, room_id BIGINT, row_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_server_constraints;
CREATE TABLE t_server_constraints (scst_id BIGINT DEFAULT nextval('t_server_constraints_scst_id_seq'::regclass) NOT NULL, scst_type CHARACTER VARYING(3), scst_title CHARACTER VARYING(20), scst_priority SMALLINT, scst_mrt_type CHARACTER VARYING(40), scst_server_name CHARACTER VARYING(8), epco_id BIGINT, scst_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_servers;
CREATE TABLE t_servers (serv_id BIGINT DEFAULT nextval('t_servers_serv_id_seq'::regclass) NOT NULL, serv_name CHARACTER VARYING(255), serv_type CHARACTER VARYING(1), serv_ip_address CHARACTER VARYING(255), node_id BIGINT, serv_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_service_commit;
CREATE TABLE t_service_commit (sc_id BIGINT DEFAULT nextval('t_service_commit_sc_id_seq'::regclass) NOT NULL, sc_entry CHARACTER VARYING(20), sc_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_service_profiles;
CREATE TABLE t_service_profiles (srpr_id BIGINT DEFAULT nextval('t_service_profiles_srpr_id_seq'::regclass) NOT NULL, srpr_card_num SMALLINT, srpr_port_num SMALLINT, srpr_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_sfp_module_port_assocs;
CREATE TABLE t_sfp_module_port_assocs (smpa_id BIGINT DEFAULT nextval('t_sfp_module_port_assocs_smpa_id_seq'::regclass) NOT NULL, smpa_creation_date DATE, smpa_creation_time INTEGER, sfpm_id BIGINT, port_id BIGINT, smpa_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_sfp_modules;
CREATE TABLE t_sfp_modules (sfpm_id BIGINT DEFAULT nextval('t_sfp_modules_sfpm_id_seq'::regclass) NOT NULL, sfpm_name CHARACTER VARYING(15), sfmp_short_name CHARACTER VARYING(10), sfmp_mode CHARACTER VARYING(10), sfpm_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_shelf_models;
CREATE TABLE t_shelf_models (shmd_id BIGINT DEFAULT nextval('t_shelf_models_shmd_id_seq'::regclass) NOT NULL, shmd_name CHARACTER VARYING(24), shmd_long_name CHARACTER VARYING(70), shmd_ean_code CHARACTER VARYING(13), shmd_remarks CHARACTER VARYING(24), shmd_family_name CHARACTER VARYING(4), shmd_port_count SMALLINT, manf_id BIGINT, shmd_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_shelfs;
CREATE TABLE t_shelfs (shlf_id BIGINT DEFAULT nextval('t_shelfs_shlf_id_seq'::regclass) NOT NULL, shlf_type CHARACTER(1), shlf_remarks CHARACTER VARYING(128), shlf_logic_shelf_num SMALLINT, shlf_shelf_bay_num SMALLINT, shlf_toc_max SMALLINT, shlf_prod_status CHARACTER VARYING(1), shlf_mutation CHARACTER VARYING(1), shlf_logic_bay_info CHARACTER VARYING(6), shlf_matrix CHARACTER VARYING(25), shlf_logic_sub_shelf_num SMALLINT, node_id BIGINT, shmd_id BIGINT, eqpt_id BIGINT, bay_id BIGINT, logical_shlf_id BIGINT, eqpt_id_delocalized INTEGER, shlf_version INTEGER DEFAULT 1 NOT NULL, shlf_creation_time TIMESTAMP(6) WITH TIME ZONE, shlf_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_sites;
CREATE TABLE t_sites (site_id BIGINT NOT NULL, site_property_code CHARACTER VARYING(6), loca_id BIGINT, site_version INTEGER DEFAULT 1 NOT NULL, site_creation_date DATE, site_creation_time INTEGER, site_last_modification_date DATE, site_last_modification_time INTEGER);
DROP TABLE t_slot_models;
CREATE TABLE t_slot_models (slmd_id BIGINT DEFAULT nextval('t_slot_models_slmd_id_seq'::regclass) NOT NULL, slmd_num SMALLINT, slmd_type CHARACTER(1), slmd_name CHARACTER VARYING(30), slmd_port_size SMALLINT, slmd_port_init SMALLINT, shmd_id BIGINT, slmd_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_slots;
CREATE TABLE t_slots (slot_id BIGINT DEFAULT nextval('t_slots_slot_id_seq'::regclass) NOT NULL, slot_num SMALLINT, slot_occup_state CHARACTER VARYING(1), slot_type CHARACTER VARYING(1), slot_name CHARACTER VARYING(30), shlf_id BIGINT, slot_version INTEGER DEFAULT 1 NOT NULL, slot_creation_time TIMESTAMP(6) WITH TIME ZONE, slot_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_st_components;
CREATE TABLE t_st_components (stco_id BIGINT DEFAULT nextval('t_st_components_stco_id_seq'::regclass) NOT NULL, stco_name CHARACTER VARYING(50), atpr_id BIGINT, tcsv_id BIGINT, tsft_id BIGINT, stco_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_stripe_models;
CREATE TABLE t_stripe_models (strm_id BIGINT DEFAULT nextval('t_stripe_models_strm_id_seq'::regclass) NOT NULL, strm_name CHARACTER VARYING(20), strm_pin_count SMALLINT, strm_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_stripes;
CREATE TABLE t_stripes (strp_id BIGINT DEFAULT nextval('t_stripes_strp_id_seq'::regclass) NOT NULL, strp_name CHARACTER VARYING(6) NOT NULL, strp_module CHARACTER VARYING(1) NOT NULL, strp_up_range SMALLINT, strp_down_range SMALLINT, strp_up_level SMALLINT, strp_down_level SMALLINT, strp_remarks CHARACTER VARYING(128), strp_free_pin_count SMALLINT NOT NULL, strp_pin_count SMALLINT NOT NULL, dist_id BIGINT, strm_id BIGINT, strp_version INTEGER DEFAULT 1 NOT NULL, strp_creation_time TIMESTAMP(6) WITH TIME ZONE, strp_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
DROP TABLE t_swap_requests;
CREATE TABLE t_swap_requests (swap_id BIGINT DEFAULT nextval('t_swap_requests_swap_id_seq'::regclass) NOT NULL, swap_version INTEGER DEFAULT 1 NOT NULL, swap_eqpt_id INTEGER NOT NULL, swap_shelf_id INTEGER NOT NULL, swap_shelf_old_state CHARACTER(1), swap_init_time TIMESTAMP(6) WITH TIME ZONE, swap_start_time TIMESTAMP(6) WITH TIME ZONE, swap_end_time TIMESTAMP(6) WITH TIME ZONE, swap_state CHARACTER(1), swap_cuid CHARACTER VARYING(8), swap_remarks CHARACTER VARYING(255));
DROP TABLE t_tech_serv_functions;
CREATE TABLE t_tech_serv_functions (tsft_id BIGINT DEFAULT nextval('t_tech_serv_functions_tsft_id_seq'::regclass) NOT NULL, tsft_function_code CHARACTER VARYING(15), tsft_co_use SMALLINT, tsft_default_vrf CHARACTER VARYING(4), tsft_thresh_chk SMALLINT, mrty_id BIGINT, tst_id BIGINT, tsft_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tech_serv_types;
CREATE TABLE t_tech_serv_types (tst_id BIGINT DEFAULT nextval('t_tech_serv_types_tst_id_seq'::regclass) NOT NULL, tst_name CHARACTER VARYING(20), tst_spi_update NUMERIC(1,0), tst_group CHARACTER(1), tst_rare_res SMALLINT, tst_servlevel CHARACTER(1), tst_create_dslam_access CHARACTER(1), tst_is_internet CHARACTER(1), tst_e1_forbidden CHARACTER(1), tst_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tech_services;
CREATE TABLE t_tech_services (tcsv_id BIGINT DEFAULT nextval('t_tech_services_tcsv_id_seq'::regclass) NOT NULL, tcsv_name CHARACTER VARYING(50), intf_id BIGINT, thro_id BIGINT, tst_id BIGINT, tcty_id BIGINT, tcsv_version INTEGER DEFAULT 1 NOT NULL, tcsv_untagged SMALLINT DEFAULT 0);
DROP TABLE t_techno_on_card_nat_profiles;
CREATE TABLE t_techno_on_card_nat_profiles (ttcn_id BIGINT DEFAULT nextval('t_techno_on_card_nat_profiles_ttcn_id_seq'::regclass) NOT NULL, cnpr_id BIGINT, tcty_id BIGINT, ttcn_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_technology_types;
CREATE TABLE t_technology_types (tcty_id BIGINT DEFAULT nextval('t_technology_types_tcty_id_seq'::regclass) NOT NULL, tcty_name CHARACTER VARYING(20), tcty_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_throughputs;
CREATE TABLE t_throughputs (thro_id BIGINT DEFAULT nextval('t_throughputs_thro_id_seq'::regclass) NOT NULL, thro_name CHARACTER VARYING(30), thro_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tp_ccl_atms;
CREATE TABLE t_tp_ccl_atms (tpcc_id BIGINT DEFAULT nextval('t_tp_ccl_atms_tpcc_id_seq'::regclass) NOT NULL, tpcc_nd CHARACTER VARYING(15), tpcc_source_ccl CHARACTER VARYING(15), tpcc_source_vc SMALLINT, tpcc_target_ccl CHARACTER VARYING(15), tpcc_target_vc SMALLINT, tpcc_source_vp SMALLINT, tpcc_target_vp SMALLINT, tps_id BIGINT, tpcc_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tp_initial_states;
CREATE TABLE t_tp_initial_states (tpis_id BIGINT DEFAULT nextval('t_tp_initial_states_tpis_id_seq'::regclass) NOT NULL, tpis_nd CHARACTER VARYING(15), tpis_initial_vp SMALLINT, tpis_initial_vc SMALLINT, tpis_target_vp SMALLINT, tpis_target_vc SMALLINT, tpis_is_new_vp SMALLINT, tp_id BIGINT, tpis_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tp_shelfs;
CREATE TABLE t_tp_shelfs (tpsf_id BIGINT DEFAULT nextval('t_tp_shelfs_tpsf_id_seq'::regclass) NOT NULL, tpsf_shelf_num_n SMALLINT, tpsf_shelf_num_n1 SMALLINT, tp_id BIGINT, tpsf_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tps;
CREATE TABLE t_tps (tp_id BIGINT DEFAULT nextval('t_tps_tp_id_seq'::regclass) NOT NULL, tp_hub_code CHARACTER VARYING(19), tp_dslam_n CHARACTER VARYING(20), tp_dslam_n1 CHARACTER VARYING(20), tp_creation_date DATE, tp_creation_time INTEGER, tp_execution_date DATE, tp_execution_time INTEGER, tp_execution_type SMALLINT, tp_status SMALLINT, tp_comments CHARACTER VARYING(255), tp_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tr_assignments;
CREATE TABLE t_tr_assignments (tass_id BIGINT DEFAULT nextval('t_tr_assignments_tass_id_seq'::regclass) NOT NULL, tass_mrt_type CHARACTER VARYING(40), tass_tr_function CHARACTER VARYING(15), tass_choice_constraint_size SMALLINT, tass_usage_constraint_size SMALLINT, epco_id BIGINT, tass_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tr_functions;
CREATE TABLE t_tr_functions (tfct_id BIGINT DEFAULT nextval('t_tr_functions_tfct_id_seq'::regclass) NOT NULL, tfct_name CHARACTER VARYING(15), tfct_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_trs;
CREATE TABLE t_trs (tr_id BIGINT DEFAULT nextval('t_trs_tr_id_seq'::regclass) NOT NULL, tfct_id BIGINT, tr_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tsf_family_assoc;
CREATE TABLE t_tsf_family_assoc (tfa_id BIGINT DEFAULT nextval('t_tsf_family_assoc_tfa_id_seq'::regclass) NOT NULL, tsft_id BIGINT NOT NULL, tfa_family CHARACTER VARYING(10) NOT NULL, tfa_version INTEGER DEFAULT 1 NOT NULL, UNIQUE (tsft_id));
DROP TABLE t_tsf_usage_assoc;
CREATE TABLE t_tsf_usage_assoc (tua_assoc_id BIGINT DEFAULT nextval('t_tsf_usage_assoc_tua_assoc_id_seq'::regclass) NOT NULL, tua_usage CHARACTER VARYING(20) NOT NULL, tua_equipment_type CHARACTER VARYING(10) NOT NULL, tua_group_localisation_id BIGINT NOT NULL, tua_vlan_interval_min CHARACTER VARYING(10), tua_vlan_interval_max CHARACTER VARYING(10), tua_tsf_id BIGINT NOT NULL, tua_manufacturer_id BIGINT NOT NULL, tua_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tst_closed_on_cards;
CREATE TABLE t_tst_closed_on_cards (scds_id BIGINT DEFAULT nextval('t_tst_closed_on_cards_scds_id_seq'::regclass) NOT NULL, scds_prod_status CHARACTER(1), tst_id BIGINT, card_id BIGINT, scds_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tst_closed_on_shelfs;
CREATE TABLE t_tst_closed_on_shelfs (scsh_id BIGINT DEFAULT nextval('t_tst_closed_on_shelfs_scsh_id_seq'::regclass) NOT NULL, scsh_prod_status CHARACTER(1), tst_id BIGINT, shlf_id BIGINT, scsh_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tst_on_card_nat_profiles;
CREATE TABLE t_tst_on_card_nat_profiles (tscn_id BIGINT DEFAULT nextval('t_tst_on_card_nat_profiles_tscn_id_seq'::regclass) NOT NULL, tscn_prod_status CHARACTER(1), cnpr_id BIGINT, tst_id BIGINT, tscn_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tst_on_dslams;
CREATE TABLE t_tst_on_dslams (sods_id BIGINT DEFAULT nextval('t_tst_on_dslams_sods_id_seq'::regclass) NOT NULL, sods_prod_status CHARACTER(1), tst_id BIGINT, eqpt_id BIGINT, sods_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_tst_without_mrts;
CREATE TABLE t_tst_without_mrts (twmt_tst_name CHARACTER VARYING(20), twmt_version INTEGER DEFAULT 1 NOT NULL, twmt_id BIGINT DEFAULT nextval('t_tst_without_mrts_twmt_id_seq'::regclass) NOT NULL);
COMMENT ON COLUMN t_tst_without_mrts.twmt_id IS 'BRASIL-439 Cle auto incremental de la table';
DROP TABLE t_usage_constraints;
CREATE TABLE t_usage_constraints (ucst_id BIGINT DEFAULT nextval('t_usage_constraints_ucst_id_seq'::regclass) NOT NULL, ucst_type CHARACTER VARYING(10), usct_title CHARACTER VARYING(20), ucst_res_rank SMALLINT, ucst_vc_min SMALLINT, ucst_vc_max SMALLINT, ucst_vp_min SMALLINT, ucst_vp_max SMALLINT, ucst_priority SMALLINT, tass_id BIGINT, ucst_version INTEGER DEFAULT 1 NOT NULL);
DROP TABLE t_vc_lock_ranges;
CREATE TABLE t_vc_lock_ranges (rpct_id BIGINT NOT NULL, vckr_vc_max INTEGER NOT NULL, vckr_vc_min INTEGER NOT NULL, vckr_version INTEGER DEFAULT 1 NOT NULL, vckr_creation_time TIMESTAMP(6) WITH TIME ZONE, vckr_last_modification_time TIMESTAMP(6) WITH TIME ZONE);
ALTER TABLE t_application_parameter_values ADD CONSTRAINT fk_t_application_parameters_appa_id FOREIGN KEY (appa_id) REFERENCES t_application_parameters (appa_id);
ALTER TABLE t_atm_profiles ADD CONSTRAINT fk_t_throughputs_thro_id FOREIGN KEY (thro_id) REFERENCES t_throughputs (thro_id);
ALTER TABLE t_bays ADD CONSTRAINT fk_t_rows_row_id FOREIGN KEY (row_id) REFERENCES t_rows (row_id);
ALTER TABLE t_card_models ADD CONSTRAINT fk_t_manufacturers_manf_id FOREIGN KEY (manf_id) REFERENCES t_manufacturers (manf_id);
ALTER TABLE t_card_national_profiles ADD CONSTRAINT fk_t_card_soft_vers_csfv_id FOREIGN KEY (csfv_id) REFERENCES t_card_soft_vers (csfv_id);
ALTER TABLE t_card_soft_vers ADD CONSTRAINT fk_t_card_soft_vers_t_card_models_cmod_id FOREIGN KEY (cmod_id) REFERENCES t_card_models (cmod_id);
ALTER TABLE t_cardmodels_sfp ADD CONSTRAINT fk_t_cardmodels_cmod_id FOREIGN KEY (cmod_id) REFERENCES t_card_models (cmod_id);
ALTER TABLE t_cards ADD CONSTRAINT fk_t_card_models_cmod_id FOREIGN KEY (cmod_id) REFERENCES t_card_models (cmod_id);
ALTER TABLE t_cards ADD CONSTRAINT fk_t_card_soft_vers_csfv_id FOREIGN KEY (csfv_id) REFERENCES t_card_soft_vers (csfv_id);
ALTER TABLE t_cards ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id_delocalized) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_cards ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_cards ADD CONSTRAINT fk_t_slots_slot_id FOREIGN KEY (slot_id) REFERENCES t_slots (slot_id);
ALTER TABLE t_d_booked_ports ADD CONSTRAINT fk_t_ports_port_id FOREIGN KEY (port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_d_controlable_rscs ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (b_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_controlable_rscs ADD CONSTRAINT fk_t_equipments_eqpt_idv2 FOREIGN KEY (a_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_controlable_rscs ADD CONSTRAINT fk_t_ports_port_id FOREIGN KEY (a_port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_d_controlable_rscs ADD CONSTRAINT fk_t_res_prod_controlables_rpct_id FOREIGN KEY (rpct_id) REFERENCES t_res_prod_controlables (rpct_id);
ALTER TABLE t_d_dslam_logical_shelfs ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_dslam_logical_shelfs ADD CONSTRAINT fk_t_equipments_eqpt_idv2 FOREIGN KEY (dslam_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_dslam_logical_shelfs ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_d_dslam_logical_shelfs ADD CONSTRAINT fk_t_shelfs_shlf_id FOREIGN KEY (shlf_id) REFERENCES t_shelfs (shlf_id);
ALTER TABLE t_d_dslam_manelems ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (source_dslam_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_dslam_manelems ADD CONSTRAINT fk_t_equipments_eqpt_idv2 FOREIGN KEY (master_dslam_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_dslam_manelems ADD CONSTRAINT fk_t_equipments_eqpt_idv3 FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_dslam_manelems ADD CONSTRAINT fk_t_equipments_eqpt_idv4 FOREIGN KEY (dslam_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_dslam_manelems ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_d_dslam_xdsl_cards ADD CONSTRAINT fk_t_card_soft_vers_csfv_id FOREIGN KEY (csfv_id) REFERENCES t_card_soft_vers (csfv_id);
ALTER TABLE t_d_dslam_xdsl_cards ADD CONSTRAINT fk_t_cards_card_id FOREIGN KEY (card_id) REFERENCES t_cards (card_id);
ALTER TABLE t_d_dslam_xdsl_cards ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (dslam_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_dslam_xdsl_cards ADD CONSTRAINT fk_t_equipments_eqpt_idv2 FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_dslam_xdsl_cards ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_d_dslam_xdsl_cards ADD CONSTRAINT fk_t_shelfs_shlf_id FOREIGN KEY (shlf_id) REFERENCES t_shelfs (shlf_id);
ALTER TABLE t_d_need_new_vcs ADD CONSTRAINT fk_t_res_prod_controlables_rpct_id FOREIGN KEY (rpct_id) REFERENCES t_res_prod_controlables (rpct_id);
ALTER TABLE t_d_rsc_dslam_tsfs ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (dslam_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_rsc_dslam_tsfs ADD CONSTRAINT fk_t_equipments_eqpt_id2 FOREIGN KEY (nip_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_rsc_dslam_tsfs ADD CONSTRAINT fk_t_res_prod_controlables_rpct_id FOREIGN KEY (rpct_id) REFERENCES t_res_prod_controlables (rpct_id);
ALTER TABLE t_d_rsc_dslam_tsfs ADD CONSTRAINT fk_t_tech_serv_functions_tsft_id FOREIGN KEY (tsft_id) REFERENCES t_tech_serv_functions (tsft_id);
ALTER TABLE t_d_rsc_vcis ADD CONSTRAINT fk_t_res_prod_controlables_rpct_id FOREIGN KEY (rpct_id) REFERENCES t_res_prod_controlables (rpct_id);
ALTER TABLE t_d_xdsl_card_stripes ADD CONSTRAINT fk_t_cards_card_id FOREIGN KEY (card_id) REFERENCES t_cards (card_id);
ALTER TABLE t_d_xdsl_card_stripes ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_d_xdsl_card_stripes ADD CONSTRAINT fk_t_stripes_strp_id FOREIGN KEY (strp_id) REFERENCES t_stripes (strp_id);
ALTER TABLE t_distributors ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_dslam_access_constraints ADD CONSTRAINT fk_t_dslam_assignments_dsag_id FOREIGN KEY (dsag_id) REFERENCES t_dslam_assignments (dsag_id);
ALTER TABLE t_dslam_assignments ADD CONSTRAINT fk_t_making_files_mkfl_id FOREIGN KEY (mkfl_id) REFERENCES t_making_files (mkfl_id);
ALTER TABLE t_dslam_soft_vers ADD CONSTRAINT fk_t_logical_eqpt_models_lgem_id FOREIGN KEY (lgem_id) REFERENCES t_logical_eqpt_models (lgem_id);
ALTER TABLE t_epc_order_lines ADD CONSTRAINT fk_t_making_files_mkfl_id FOREIGN KEY (mkfl_id) REFERENCES t_making_files (mkfl_id);
ALTER TABLE t_epc_vers ADD CONSTRAINT fk_t_epcs_epc_id FOREIGN KEY (epc_id) REFERENCES t_epcs (epc_id);
ALTER TABLE t_epc_vers ADD CONSTRAINT fk_t_mrt_access_dslams_mrtd_id FOREIGN KEY (mrtd_id) REFERENCES t_mrt_access_dslams (mrtd_id);
ALTER TABLE t_epc_vers ADD CONSTRAINT fk_t_tech_services_tcsv_id FOREIGN KEY (tcsv_id) REFERENCES t_tech_services (tcsv_id);
ALTER TABLE t_epc_vers_comps ADD CONSTRAINT fk_t_epc_vers_epcv_id FOREIGN KEY (epcv_id) REFERENCES t_epc_vers (epcv_id);
ALTER TABLE t_epc_vers_comps ADD CONSTRAINT fk_t_mrt_access_dslam_vers_mrdv_id_1 FOREIGN KEY (mrdv_id) REFERENCES t_mrt_access_dslam_vers (mrdv_id);
ALTER TABLE t_epc_vers_comps ADD CONSTRAINT fk_t_mrt_access_service_vers_mrsv_id FOREIGN KEY (mrsv_id) REFERENCES t_mrt_access_service_vers (mrsv_id);
ALTER TABLE t_epc_vers_comps ADD CONSTRAINT fk_t_st_components_stco_id FOREIGN KEY (stco_id) REFERENCES t_st_components (stco_id);
ALTER TABLE t_epc_vers_impacts ADD CONSTRAINT fk_t_epc_vers_epcv_id FOREIGN KEY (epcv_id) REFERENCES t_epc_vers (epcv_id);
ALTER TABLE t_epc_vers_impacts ADD CONSTRAINT fk_t_making_files_mkfl_id FOREIGN KEY (mkfl_id) REFERENCES t_making_files (mkfl_id);
ALTER TABLE t_eqpt_shf_mdl_compatibilities ADD CONSTRAINT fk_t_logical_eqpt_models_lgem_id FOREIGN KEY (lgem_id) REFERENCES t_logical_eqpt_models (lgem_id);
ALTER TABLE t_eqpt_shf_mdl_compatibilities ADD CONSTRAINT fk_t_shelf_models_shmd_id FOREIGN KEY (shmd_id) REFERENCES t_shelf_models (shmd_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_dslam_soft_vers_dssv_id FOREIGN KEY (dssv_id) REFERENCES t_dslam_soft_vers (dssv_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (manager_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_equipments_eqpt_idv1 FOREIGN KEY (source_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_equipments_eqpt_idv2 FOREIGN KEY (master_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_equipments_eqpt_idv3 FOREIGN KEY (eqpt_id_real_dslam) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_nodes_node_idv2 FOREIGN KEY (node_id_delocalized) REFERENCES t_nodes (node_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_logical_eqpt_models_lgem_id FOREIGN KEY (lgem_id) REFERENCES t_logical_eqpt_models (lgem_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_manufacturers_manf_id FOREIGN KEY (manf_id) REFERENCES t_manufacturers (manf_id);
ALTER TABLE t_equipments ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_es ADD CONSTRAINT fk_t_es_types_est_id FOREIGN KEY (est_id) REFERENCES t_es_types (est_id);
ALTER TABLE t_es_habilitations ADD CONSTRAINT fk_t_es_types_est_idv2 FOREIGN KEY (est_id) REFERENCES t_es_types (est_id);
ALTER TABLE t_es_logs ADD CONSTRAINT fk_t_es_es_id FOREIGN KEY (es_id) REFERENCES t_es (es_id);
ALTER TABLE t_es_types ADD CONSTRAINT fk_t_es_connexions_esc_id FOREIGN KEY (esc_id) REFERENCES t_es_connexions (esc_id);
ALTER TABLE t_ftth_lock_onts ADD CONSTRAINT fk_t_ports_port_id FOREIGN KEY (port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_icc_updates ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_link_dr_group_localisation ADD CONSTRAINT fk_t_link_dr_group_localisation_dr_code FOREIGN KEY (dr_code) REFERENCES t_dr (dr_code);
ALTER TABLE t_link_dr_group_localisation ADD CONSTRAINT fk_t_link_dr_group_localisation_group_id FOREIGN KEY (group_localisation_id) REFERENCES t_group_localisation (group_localisation_id);
ALTER TABLE t_logical_eqpt_models ADD CONSTRAINT fk_t_manufacturers_manf_id FOREIGN KEY (manf_id) REFERENCES t_manufacturers (manf_id);
ALTER TABLE t_making_files ADD CONSTRAINT fk_t_operators_oper_id FOREIGN KEY (oper_id) REFERENCES t_operators (oper_id);
ALTER TABLE t_media_links ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (b_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_media_links ADD CONSTRAINT fk_t_equipments_eqpt_idv1 FOREIGN KEY (a_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_media_links ADD CONSTRAINT fk_t_equipments_eqpt_idv2 FOREIGN KEY (ce_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_media_links ADD CONSTRAINT fk_t_function_codes_fctc_id FOREIGN KEY (fctc_id) REFERENCES t_function_codes (fctc_id);
ALTER TABLE t_media_links ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (a_node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_media_links ADD CONSTRAINT fk_t_nodes_node_idv2 FOREIGN KEY (b_node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_media_links ADD CONSTRAINT fk_t_ports_port_id FOREIGN KEY (a_port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_media_links ADD CONSTRAINT fk_t_ports_port_idv2 FOREIGN KEY (b_port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_mrt_access_dslam_vers ADD CONSTRAINT fk_t_line_profiles_lnpr_id FOREIGN KEY (lnpr_id) REFERENCES t_line_profiles (lnpr_id);
ALTER TABLE t_mrt_access_dslam_vers ADD CONSTRAINT fk_t_ont_profiles_ontp_id FOREIGN KEY (ontp_id) REFERENCES t_ont_profiles (ontp_id);
ALTER TABLE t_mrt_access_dslam_vers ADD CONSTRAINT fk_t_mrt_access_dslams_mrtd_id FOREIGN KEY (mrtd_id) REFERENCES t_mrt_access_dslams (mrtd_id);
ALTER TABLE t_mrt_access_dslams ADD CONSTRAINT fk_t_equipments_eqpt_idv1 FOREIGN KEY (a_eqpt_id) REFERENCES t_equipments (eqpt_id) ON DELETE CASCADE;
ALTER TABLE t_mrt_access_dslams ADD CONSTRAINT fk_t_mrt_types_mrty_id FOREIGN KEY (mrty_id) REFERENCES t_mrt_types (mrty_id);
ALTER TABLE t_mrt_access_dslams ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (a_node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_mrt_access_dslams ADD CONSTRAINT fk_t_operators_oper_id FOREIGN KEY (oper_id) REFERENCES t_operators (oper_id);
ALTER TABLE t_mrt_access_dslams ADD CONSTRAINT fk_t_ports_port_id FOREIGN KEY (a_port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_mrt_access_dslams ADD CONSTRAINT fk_t_port_groups_pogr_id FOREIGN KEY (a_pogr_id) REFERENCES t_port_groups (pogr_id);
ALTER TABLE t_mrt_access_dslams ADD CONSTRAINT fk_t_technology_types_tcty_id FOREIGN KEY (tcty_id) REFERENCES t_technology_types (tcty_id);
ALTER TABLE t_mrt_access_msan_usage ADD CONSTRAINT fk_t_mrt_access_msan_usage_mrdv_id FOREIGN KEY (mrdv_id) REFERENCES t_mrt_access_dslam_vers (mrdv_id);
ALTER TABLE t_mrt_access_service_vers ADD CONSTRAINT fk_t_atm_profiles_atpr_id FOREIGN KEY (atpr_id) REFERENCES t_atm_profiles (atpr_id);
ALTER TABLE t_mrt_access_service_vers ADD CONSTRAINT fk_t_mrt_access_services_mras_id FOREIGN KEY (mras_id) REFERENCES t_mrt_access_services (mras_id);
ALTER TABLE t_mrt_access_service_vers ADD CONSTRAINT fk_t_service_profiles_srpr_id FOREIGN KEY (srpr_id) REFERENCES t_service_profiles (srpr_id);
ALTER TABLE t_mrt_access_services ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_mrt_access_services ADD CONSTRAINT fk_t_mrt_types_mrty_id FOREIGN KEY (mrty_id) REFERENCES t_mrt_types (mrty_id);
ALTER TABLE t_mrt_access_services ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (a_node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_mrt_access_services ADD CONSTRAINT fk_t_operators_oper_id FOREIGN KEY (oper_id) REFERENCES t_operators (oper_id);
ALTER TABLE t_mrt_vers_impacts ADD CONSTRAINT fk_t_making_files_mkfl_id FOREIGN KEY (mkfl_id) REFERENCES t_making_files (mkfl_id);
ALTER TABLE t_mrt_vers_impacts ADD CONSTRAINT fk_t_mrt_access_dslam_vers_mrdv_id FOREIGN KEY (mrdv_id) REFERENCES t_mrt_access_dslam_vers (mrdv_id);
ALTER TABLE t_mrt_vers_impacts ADD CONSTRAINT fk_t_mrt_access_service_vers_mrsv_id FOREIGN KEY (mrsv_id) REFERENCES t_mrt_access_service_vers (mrsv_id);
ALTER TABLE t_net_port_models ADD CONSTRAINT fk_t_card_models_cmod_id FOREIGN KEY (cmod_id) REFERENCES t_card_models (cmod_id);
ALTER TABLE t_net_resource_rels ADD CONSTRAINT fk_t_operators_oper_id FOREIGN KEY (oper_id) REFERENCES t_operators (oper_id);
ALTER TABLE t_net_resource_rels ADD CONSTRAINT fk_t_res_prod_controlables_rpct_id FOREIGN KEY (rpct_id) REFERENCES t_res_prod_controlables (rpct_id);
ALTER TABLE t_nip_server_assocs ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_nip_server_assocs ADD CONSTRAINT fk_t_servers_serv_id FOREIGN KEY (serv_id) REFERENCES t_servers (serv_id);
ALTER TABLE t_nip_server_assocs ADD CONSTRAINT fk_t_tech_serv_types_tst_id FOREIGN KEY (tst_id) REFERENCES t_tech_serv_types (tst_id);
ALTER TABLE t_no_back_on_technos ADD CONSTRAINT fk_t_distributors_dist_id FOREIGN KEY (dist_id) REFERENCES t_distributors (dist_id);
ALTER TABLE t_no_back_on_technos ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_no_back_on_technos ADD CONSTRAINT fk_t_technology_types_tcty_id FOREIGN KEY (tcty_id) REFERENCES t_technology_types (tcty_id);
ALTER TABLE t_nodes ADD CONSTRAINT fk_t_sites_site_id FOREIGN KEY (site_id) REFERENCES t_sites (site_id);
ALTER TABLE t_nodes ADD CONSTRAINT fk_t_nodes_dr_code FOREIGN KEY (node_dr_code) REFERENCES t_dr (dr_code);
ALTER TABLE t_ports ADD CONSTRAINT fk_t_cards_card_id FOREIGN KEY (card_id) REFERENCES t_cards (card_id);
ALTER TABLE t_ports ADD CONSTRAINT fk_t_media_links_mdlk_id FOREIGN KEY (pogr_id) REFERENCES t_port_groups (pogr_id);
ALTER TABLE t_ports ADD CONSTRAINT fk_t_prestations_prst_id FOREIGN KEY (prst_id) REFERENCES t_prestations (prst_id);
ALTER TABLE t_ports ADD CONSTRAINT fk_t_slots_slot_id FOREIGN KEY (slot_id) REFERENCES t_slots (slot_id);
ALTER TABLE t_ports ADD CONSTRAINT fk_t_stripes_strp_id FOREIGN KEY (strp_id) REFERENCES t_stripes (strp_id);
ALTER TABLE t_ports ADD CONSTRAINT fk_t_tech_serv_types_tst_id FOREIGN KEY (tst_id) REFERENCES t_tech_serv_types (tst_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (ce_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_equipments_eqpt_idv2 FOREIGN KEY (a_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_equipments_eqpt_idv3 FOREIGN KEY (b_eqpt_id) REFERENCES t_equipments (eqpt_id) ON DELETE CASCADE;
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_mrt_types_mrty_id FOREIGN KEY (mrty_id) REFERENCES t_mrt_types (mrty_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (a_node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_nodes_node_idv2 FOREIGN KEY (b_node_id) REFERENCES t_nodes (node_id) ON DELETE CASCADE;
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_ports_port_id FOREIGN KEY (b_port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_ports_port_idv2 FOREIGN KEY (a_port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_port_groups_pogr_id FOREIGN KEY (a_pogr_id) REFERENCES t_port_groups (pogr_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_port_groups_b_pogr_id FOREIGN KEY (b_pogr_id) REFERENCES t_port_groups (pogr_id);
ALTER TABLE t_res_prod_controlables ADD CONSTRAINT fk_t_roles_role_id FOREIGN KEY (role_id) REFERENCES t_roles (role_id);
ALTER TABLE t_res_prod_controlers ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_res_prod_controlers ADD CONSTRAINT fk_t_tech_serv_functions_tsft_id FOREIGN KEY (tsft_id) REFERENCES t_tech_serv_functions (tsft_id);
ALTER TABLE t_res_prod_roles ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (dslam_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_res_prod_roles ADD CONSTRAINT fk_t_equipments_eqpt_idv2 FOREIGN KEY (nip_eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_res_prod_roles ADD CONSTRAINT fk_t_res_prod_controlables_rpct_id FOREIGN KEY (rpct_id) REFERENCES t_res_prod_controlables (rpct_id);
ALTER TABLE t_res_prod_roles ADD CONSTRAINT fk_t_res_prod_controlers_rpco_id FOREIGN KEY (rpco_id) REFERENCES t_res_prod_controlers (rpco_id);
ALTER TABLE t_res_prod_roles ADD CONSTRAINT fk_t_tech_serv_functions_tsft_id FOREIGN KEY (tsft_id) REFERENCES t_tech_serv_functions (tsft_id);
ALTER TABLE t_resource_constraints ADD CONSTRAINT fk_t_tr_assignments_tass_id FOREIGN KEY (tass_id) REFERENCES t_tr_assignments (tass_id);
ALTER TABLE t_resource_usages ADD CONSTRAINT fk_t_mrt_access_dslams_mrtd_id FOREIGN KEY (mrtd_id) REFERENCES t_mrt_access_dslams (mrtd_id);
ALTER TABLE t_resource_usages ADD CONSTRAINT fk_t_mrt_access_services_mras_id FOREIGN KEY (mras_id) REFERENCES t_mrt_access_services (mras_id);
ALTER TABLE t_resource_usages ADD CONSTRAINT fk_t_res_prod_controlables_rpct_id FOREIGN KEY (rpct_id) REFERENCES t_res_prod_controlables (rpct_id);
ALTER TABLE t_resource_usages ADD CONSTRAINT fk_t_trs_tr_id FOREIGN KEY (tr_id) REFERENCES t_trs (tr_id);
ALTER TABLE t_rooms ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_rows ADD CONSTRAINT fk_t_rooms_room_id FOREIGN KEY (room_id) REFERENCES t_rooms (room_id);
ALTER TABLE t_server_constraints ADD CONSTRAINT fk_t_epc_order_lines_epco_id FOREIGN KEY (epco_id) REFERENCES t_epc_order_lines (epco_id);
ALTER TABLE t_servers ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_sfp_module_port_assocs ADD CONSTRAINT fk_t_ports_port_id FOREIGN KEY (port_id) REFERENCES t_ports (port_id);
ALTER TABLE t_sfp_module_port_assocs ADD CONSTRAINT fk_t_sfp_modules_sfpm_id FOREIGN KEY (sfpm_id) REFERENCES t_sfp_modules (sfpm_id);
ALTER TABLE t_shelf_models ADD CONSTRAINT fk_t_manufacturers_manf_id FOREIGN KEY (manf_id) REFERENCES t_manufacturers (manf_id);
ALTER TABLE t_shelfs ADD CONSTRAINT fk_t_bays_bay_id FOREIGN KEY (bay_id) REFERENCES t_bays (bay_id);
ALTER TABLE t_shelfs ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_shelfs ADD CONSTRAINT fk_t_equipments_eqpt_id2 FOREIGN KEY (eqpt_id_delocalized) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_shelfs ADD CONSTRAINT fk_t_nodes_node_id FOREIGN KEY (node_id) REFERENCES t_nodes (node_id);
ALTER TABLE t_shelfs ADD CONSTRAINT fk_t_shelf_models_shmd_id FOREIGN KEY (shmd_id) REFERENCES t_shelf_models (shmd_id);
ALTER TABLE t_shelfs ADD CONSTRAINT fk_t_shelfs_shlf_id FOREIGN KEY (logical_shlf_id) REFERENCES t_shelfs (shlf_id);
ALTER TABLE t_sites ADD CONSTRAINT fk_t_local_areas_loca_id FOREIGN KEY (loca_id) REFERENCES t_local_areas (loca_id);
ALTER TABLE t_slot_models ADD CONSTRAINT fk_t_shelf_models_shmd_id FOREIGN KEY (shmd_id) REFERENCES t_shelf_models (shmd_id);
ALTER TABLE t_slots ADD CONSTRAINT fk_t_shelfs_shlf_id FOREIGN KEY (shlf_id) REFERENCES t_shelfs (shlf_id);
ALTER TABLE t_st_components ADD CONSTRAINT fk_t_atm_profiles_atpr_id FOREIGN KEY (atpr_id) REFERENCES t_atm_profiles (atpr_id);
ALTER TABLE t_st_components ADD CONSTRAINT fk_t_tech_serv_functions_tsft_id FOREIGN KEY (tsft_id) REFERENCES t_tech_serv_functions (tsft_id);
ALTER TABLE t_st_components ADD CONSTRAINT fk_t_tech_services_tcsv_id FOREIGN KEY (tcsv_id) REFERENCES t_tech_services (tcsv_id);
ALTER TABLE t_stripes ADD CONSTRAINT fk_t_distributors_dist_id FOREIGN KEY (dist_id) REFERENCES t_distributors (dist_id);
ALTER TABLE t_stripes ADD CONSTRAINT fk_t_stripe_models_strm_id FOREIGN KEY (strm_id) REFERENCES t_stripe_models (strm_id);
ALTER TABLE t_tech_serv_functions ADD CONSTRAINT fk_t_mrt_types_mrty_id FOREIGN KEY (mrty_id) REFERENCES t_mrt_types (mrty_id);
ALTER TABLE t_tech_serv_functions ADD CONSTRAINT fk_t_tech_serv_types_tst_id FOREIGN KEY (tst_id) REFERENCES t_tech_serv_types (tst_id);
ALTER TABLE t_tech_services ADD CONSTRAINT fk_t_interfaces_intf_id FOREIGN KEY (intf_id) REFERENCES t_interfaces (intf_id);
ALTER TABLE t_tech_services ADD CONSTRAINT fk_t_tech_serv_types_tst_id FOREIGN KEY (tst_id) REFERENCES t_tech_serv_types (tst_id);
ALTER TABLE t_tech_services ADD CONSTRAINT fk_t_technology_types_tcty_id FOREIGN KEY (tcty_id) REFERENCES t_technology_types (tcty_id);
ALTER TABLE t_tech_services ADD CONSTRAINT fk_t_throughputs_thro_id FOREIGN KEY (thro_id) REFERENCES t_throughputs (thro_id);
ALTER TABLE t_techno_on_card_nat_profiles ADD CONSTRAINT fk_t_card_national_profiles_cnpr_id FOREIGN KEY (cnpr_id) REFERENCES t_card_national_profiles (cnpr_id);
ALTER TABLE t_techno_on_card_nat_profiles ADD CONSTRAINT fk_t_technology_types_tcty_id FOREIGN KEY (tcty_id) REFERENCES t_technology_types (tcty_id);
ALTER TABLE t_tp_ccl_atms ADD CONSTRAINT fk_t_tps_tp_id FOREIGN KEY (tps_id) REFERENCES t_tps (tp_id);
ALTER TABLE t_tp_initial_states ADD CONSTRAINT fk_t_tps_tp_id FOREIGN KEY (tp_id) REFERENCES t_tps (tp_id);
ALTER TABLE t_tp_shelfs ADD CONSTRAINT fk_t_tps_tp_id FOREIGN KEY (tp_id) REFERENCES t_tps (tp_id);
ALTER TABLE t_tr_assignments ADD CONSTRAINT fk_t_epc_order_lines_epco_id FOREIGN KEY (epco_id) REFERENCES t_epc_order_lines (epco_id);
ALTER TABLE t_trs ADD CONSTRAINT fk_t_tr_functions_tfct_id FOREIGN KEY (tfct_id) REFERENCES t_tr_functions (tfct_id);
ALTER TABLE t_tsf_family_assoc ADD CONSTRAINT fk_t_tsf_family_assoc_tsft_id FOREIGN KEY (tsft_id) REFERENCES t_tech_serv_functions (tsft_id);
ALTER TABLE t_tsf_usage_assoc ADD CONSTRAINT fk_t_tsf_usage_assoc_group_id FOREIGN KEY (tua_group_localisation_id) REFERENCES t_group_localisation (group_localisation_id);
ALTER TABLE t_tsf_usage_assoc ADD CONSTRAINT fk_t_tsf_usage_assoc_manufacturer_id FOREIGN KEY (tua_manufacturer_id) REFERENCES t_manufacturers (manf_id);
ALTER TABLE t_tsf_usage_assoc ADD CONSTRAINT fk_t_tsf_usage_assoc_tst_id FOREIGN KEY (tua_tsf_id) REFERENCES t_tech_serv_functions (tsft_id);
ALTER TABLE t_tst_closed_on_cards ADD CONSTRAINT fk_t_cards_card_id FOREIGN KEY (card_id) REFERENCES t_cards (card_id);
ALTER TABLE t_tst_closed_on_cards ADD CONSTRAINT fk_t_tech_serv_types_tst_id FOREIGN KEY (tst_id) REFERENCES t_tech_serv_types (tst_id);
ALTER TABLE t_tst_closed_on_shelfs ADD CONSTRAINT fk_t_shelfs_shlf_id FOREIGN KEY (shlf_id) REFERENCES t_shelfs (shlf_id);
ALTER TABLE t_tst_closed_on_shelfs ADD CONSTRAINT fk_t_tech_serv_types_tst_id FOREIGN KEY (tst_id) REFERENCES t_tech_serv_types (tst_id);
ALTER TABLE t_tst_on_card_nat_profiles ADD CONSTRAINT fk_t_card_national_profiles_cnpr_id FOREIGN KEY (cnpr_id) REFERENCES t_card_national_profiles (cnpr_id);
ALTER TABLE t_tst_on_card_nat_profiles ADD CONSTRAINT fk_t_tech_serv_types_tst_id FOREIGN KEY (tst_id) REFERENCES t_tech_serv_types (tst_id);
ALTER TABLE t_tst_on_dslams ADD CONSTRAINT fk_t_equipments_eqpt_id FOREIGN KEY (eqpt_id) REFERENCES t_equipments (eqpt_id);
ALTER TABLE t_tst_on_dslams ADD CONSTRAINT fk_t_tech_serv_types_tst_id FOREIGN KEY (tst_id) REFERENCES t_tech_serv_types (tst_id);
ALTER TABLE t_usage_constraints ADD CONSTRAINT fk_t_tr_assignments_tass_id FOREIGN KEY (tass_id) REFERENCES t_tr_assignments (tass_id);
ALTER TABLE t_vc_lock_ranges ADD CONSTRAINT fk_t_res_prod_controlables_rpct_id FOREIGN KEY (rpct_id) REFERENCES t_res_prod_controlables (rpct_id);
DROP VIEW pg_stat_statements;
CREATE VIEW pg_stat_statements (userid, dbid, queryid, query, calls, total_time, rows, shared_blks_hit, shared_blks_read, shared_blks_dirtied, shared_blks_written, local_blks_hit, local_blks_read, local_blks_dirtied, local_blks_written, temp_blks_read, temp_blks_written, blk_read_time, blk_write_time) AS null;
DROP VIEW v;
CREATE VIEW v (iddslam, nomdslam, nid, codebase42c, codecentre42c, codedr, agglocourt, agglolong) AS  SELECT te.eqpt_id AS iddslam,
    te.eqpt_name AS nomdslam,
    tn.node_id AS nid,
    tn.node_base_code42c AS codebase42c,
    tn.node_center_code42c AS codecentre42c,
    tn.node_dr_code AS codedr,
    tla.loca_local_area_short_name AS agglocourt,
    tla.loca_local_area_long_name AS agglolong
   FROM t_equipments te,
    t_nodes tn,
    t_sites ts,
    t_local_areas tla
  WHERE ((((te.node_id = tn.node_id) AND (tn.site_id = ts.site_id)) AND (ts.loca_id = tla.loca_id)) AND ((te.eqpt_name)::text = ANY ((ARRAY['DS1EM101'::character varying, 'DS1DR101'::character varying, 'DSYXM101'::character varying, 'DSTHM101'::character varying, 'DSAG9101'::character varying, 'DSS55101'::character varying, 'DSFB1101'::character varying, 'DSC69101'::character varying, 'DSP3F101'::character varying, 'DSNY4101'::character varying, 'DS9BD101'::character varying, 'DSVMM101'::character varying])::text[])));
DROP FUNCTION braproc_changecardmodel;
--/
CREATE FUNCTION braproc_changecardmodel ()  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 
    	w_eqptLog				CHAR(70);
		w_chassisNo				smallint;
		w_chassisId				BIGINT;
		w_cardNo				smallint;
		w_newCardModel			CHAR(24);
		w_oldCardModel			CHAR(24);
		w_newCardModelFamille	CHAR(24);
		w_oldCardModelFamille	CHAR(24);
		w_newSWVersion			CHAR(20);
		w_oldSWVersion			CHAR(20);
		w_newSfpmShortName      CHAR(10);
		w_newSfpmId             BIGINT;
		w_changePortSpf         INTEGER;
		w_oldchangePortSpf      INTEGER;

		w_cardNumber			INTEGER;
		w_updCounterCard		BIGINT;
		w_cardId				BIGINT;
		w_oldSWVersionId		BIGINT;
		w_oldCardModId			BIGINT;
		w_oldHwVersion			CHAR(2);
		w_newCardModId			BIGINT;
		w_hwVersion				CHAR(2);
		w_oldPCPModelNumber		INTEGER;
		w_newPCPModelNumber		INTEGER;
		w_newSWVersionId		BIGINT;
		w_cardType				CHAR(10);
		w_sfpmName              CHAR(15);
        w_sfpmNameCard          CHAR(15);

		w_SQL_error_num			INTEGER;
		w_ligne  				RECORD;
		w_result 				INTEGER;
		w_nbrLigne 				INTEGER;
		w_slot_id				BIGINT;
		w_slotType				CHAR(8);
		w_newCardModelType		CHAR(24);
		
		w_portToUpdateId		BIGINT;
		cur_portsToUpdate 		CURSOR(p_card_id INTEGER) 
 								FOR SELECT port_id FROM t_ports WHERE card_id = p_card_id;
 		w_minCardNumber	 		INTEGER;
 		w_minPortNumber	 		INTEGER;
 		w_firtPortId			BIGINT;
 		
 		w_arrayCahssis			BIGINT[][];
		w_currentChassis		BIGINT[];
		w_existChassis 			boolean := false;
BEGIN	 
		
	--
	-- parcourir les lignes de la table
	--
	
  	FOR w_ligne IN SELECT eqptLog, shelfNo, cardNo, newCardModel, newSWVersion, newSfpmShortName FROM changeCardModelInputTable 
  	LOOP
		BEGIN
		--
		-- initialisation des informations de la carte
		--

		w_eqptLog			:= w_ligne.eqptLog;
		w_chassisNo			:= w_ligne.shelfNo;
		w_cardNo			:= w_ligne.cardNo;
		w_newCardModel		:= w_ligne.newCardModel;
		w_newSWVersion		:= w_ligne.newSWVersion;
		w_newSfpmShortName	:= w_ligne.newSfpmShortName;
		w_cardId := NULL;
		w_oldCardModId := NULL;
		w_oldSWVersionId := NULL;
		w_newCardModId := NULL;
		w_newSWVersionId := NULL;
		w_newSfpmId := NULL;
		w_result := 0;
		w_oldchangePortSpf:= 0;
		w_changePortSpf:= 0;
		
		-- vidange de la table temporaire changePortTable
		DELETE FROM changePortTable;
		

         SELECT c.card_id, c.cmod_id, c.csfv_id
		  INTO w_cardId, w_oldCardModId, w_oldSWVersionId
		  FROM t_cards c 
		  JOIN t_slots sl ON c.slot_id = sl.slot_id 
		  JOIN t_shelfs s ON sl.shlf_id = s.shlf_id
		  JOIN t_equipments e ON e.eqpt_id = s.eqpt_id
		WHERE e.eqpt_name = w_eqptLog							
		  AND s.shlf_logic_shelf_num = w_chassisNo		
		  AND c.card_num = w_cardNo;

		SELECT ttt.tcty_name
		  INTO w_cardType 
		  FROM t_card_national_profiles tcnp
		  JOIN t_techno_on_card_nat_profiles ttocnp ON tcnp.cnpr_id = ttocnp.cnpr_id
		  JOIN t_technology_types ttt ON ttocnp.tcty_id = ttt.tcty_id
		 WHERE tcnp.csfv_id = w_oldSWVersionId; 

		--
		-- validation de la ligne
		--
		IF((w_eqptLog IS NULL) OR (w_chassisNo IS NULL) OR (w_cardNo IS NULL) OR (w_newCardModel IS NULL) OR (w_newSWVersion IS NULL))  THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, w_newSfpmShortName, w_newSfpmId, w_cardType,
					'KO', 'Format de la ligne dans le fichier incorrect', '2');				 
			 CONTINUE;
		END IF;
			
		IF((w_eqptLog IS NULL) OR (LENGTH(w_eqptLog) != 8))  THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, w_newSfpmShortName, w_newSfpmId,w_cardType,
					'KO', 'Dslam ' || w_eqptLog || 'ne correspond pas au format', '2');				 
			CONTINUE;
		END IF;
		
		--
		-- recherche et validation des informations initiales de la carte
		--		
			
		 w_cardNumber = 0;
		--BRASIL-440 - ini:
		--SELECT	count(*)
		--INTO	w_cardNumber
		--FROM	t_cards c, t_shelfs s, t_equipments e, t_slots sl
		--WHERE	c.slot_id = sl.slot_id
		--AND		sl.shlf_id = s.shlf_id
		--AND		e.eqpt_id = s.eqpt_id
		--AND 	e.eqpt_name = w_eqptLog							
		--AND		s.shlf_logic_shelf_num = w_chassisNo		
		--AND		c.card_num = w_cardNo;
		SELECT COUNT(*)
		  INTO w_cardNumber
		  FROM t_cards c
		  JOIN t_slots sl ON c.slot_id = sl.slot_id
		  JOIN t_shelfs s ON sl.shlf_id = s.shlf_id
		  JOIN t_equipments e ON e.eqpt_id = s.eqpt_id
		 WHERE e.eqpt_name = w_eqptLog							
		   AND s.shlf_logic_shelf_num = w_chassisNo		
		   AND c.card_num = w_cardNo; 	
		--BRASIL-440 - fin:							
		IF	w_cardNumber = 0
		
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, w_newSfpmShortName, w_newSfpmId,w_cardType,
					'WN', 'Carte inexistante', '98');	
			CONTINUE;
		END IF;
		
		IF	w_cardNumber > 1
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, w_newSfpmShortName, w_newSfpmId, w_cardType
					'WN', 'Plusieurs cartes trouvées', '98');
			 	
			CONTINUE;
		END IF;	
		
		--
		-- recuperation des informations du carte
		--
		--BRASIL-440 - ini:
		--SELECT	c.card_id, c.cmod_id, c.csfv_id
		--INTO	w_cardId, w_oldCardModId, w_oldSWVersionId
		--FROM	t_cards c, t_shelfs s, t_equipments e, t_slots sl
		--WHERE	c.slot_id = sl.slot_id
		--AND		sl.shlf_id = s.shlf_id
		--AND		e.eqpt_id = s.eqpt_id
		--AND 	e.eqpt_name = w_eqptLog							
		--AND		s.shlf_logic_shelf_num = w_chassisNo		
		--AND		c.card_num = w_cardNo;
		
		SELECT c.card_id, c.cmod_id, c.csfv_id
		  INTO w_cardId, w_oldCardModId, w_oldSWVersionId
		  FROM t_cards c 
		  JOIN t_slots sl ON c.slot_id = sl.slot_id 
		  JOIN t_shelfs s ON sl.shlf_id = s.shlf_id
		  JOIN t_equipments e ON e.eqpt_id = s.eqpt_id
		WHERE e.eqpt_name = w_eqptLog							
		  AND s.shlf_logic_shelf_num = w_chassisNo		
		  AND c.card_num = w_cardNo;
		--BRASIL-440 - fin:
		
		--
		-- Recherche des informations du chassis et du slot
		--
		
		 w_chassisId := NULL;

		--BRASIL-440 - ini:
		--SELECT	chassis.shlf_id, slot.slot_id, slot.slot_type
		--INTO	w_chassisId, w_slot_id, w_slotType
		--FROM	t_shelfs chassis, t_slots slot, t_cards c
		--WHERE	c.card_id = w_cardId
		--AND		slot.shlf_id = chassis.shlf_id
		--AND 	c.slot_id = slot.slot_id
		--AND 	chassis.shlf_logic_shelf_num = w_chassisNo;
		
		SELECT chassis.shlf_id, slot.slot_id, slot.slot_type
		  INTO w_chassisId, w_slot_id, w_slotType   
		  FROM t_shelfs chassis
		  JOIN t_slots slot ON slot.shlf_id = chassis.shlf_id
		  JOIN t_cards c ON c.slot_id = slot.slot_id 
		 WHERE c.card_id = w_cardId
		   AND chassis.shlf_logic_shelf_num = w_chassisNo;
		--BRASIL-440 - fin:
		IF	w_chassisId IS NULL
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, w_newSfpmShortName, w_newSfpmId,w_cardType,
					'WN', 'Cas2: Chassis de rattachement non trouve', '98');			 
			CONTINUE;
		END IF;
		
		--
		-- Recherche de l'ancien version
		--
		
		SELECT	csfv_name
		INTO	w_oldSWVersion
		FROM	t_card_soft_vers
		WHERE	csfv_id = w_oldSWVersionId;
		
		--
		-- Recherche de l'ancien modèle 
		--
		SELECT	cmod_id, cmod_type, cmod_name, cmod_family_name
		INTO	w_oldCardModId, w_oldHwVersion, w_oldCardModel,w_oldCardModelFamille
		FROM	t_card_models
		WHERE	cmod_id = w_oldCardModId;
		
		--
		-- Recherche de nouveau modèle 
		--
		SELECT	cmod_id, cmod_type , cmod_family_name
		INTO	w_newCardModId, w_hwVersion, w_newCardModelFamille
		FROM	t_card_models
		WHERE	cmod_name = w_newCardModel;   
		
		IF	w_newCardModId IS NULL
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, w_newSfpmShortName, w_newSfpmId,w_cardType,
					'WN', 'Nouveau modèle de carte inexistant / modèle de carte cible inexistant', '98');
			 
			CONTINUE;
		END IF;
		
		--
		-- recherche du nouveau SWVersion
		--
		
		SELECT	csfv_id
		INTO	w_newSWVersionId
		FROM	t_card_soft_vers
		WHERE	csfv_name = w_newSWVersion
		AND		cmod_id = w_newCardModId;
		
		IF	w_newSWVersionId IS NULL
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, w_newSfpmShortName, w_newSfpmId,w_cardType,
					'WN', 'Nouvelle version logicielle inexistante / version logicielle cible inexistante', '98');
			 
			CONTINUE;
		END IF;
		--
		-- Recherche nombre de pcpmodel avant/apres
		--
		
		w_oldPCPModelNumber := 0;
		w_newPCPModelNumber := 0;
		
		SELECT	cmod_port_size
		INTO	w_oldPCPModelNumber
		FROM	t_card_models
		WHERE	cmod_id = w_oldCardModId;

		SELECT	cmod_port_size
		INTO	w_newPCPModelNumber
		FROM	t_card_models
		WHERE	cmod_id = w_newCardModId;
		
		--
		-- Recherche nombre de SPF Module avant
		--

      SELECT COUNT(*)
	   INTO w_changePortSpf
       FROM t_sfp_module_port_assocs  portSpf
       JOIN t_ports p ON p.port_id = portSpf.port_id
       WHERE   p.card_id = w_cardId AND portSpf.sfpm_id <> w_newSfpmId;  

		--
		-- determiner quel cas nous devons traiter, carte XDSL ou FTTH 
		--
		--BRASIL-440 - ini:
		--SELECT ttt.tcty_name
		--INTO w_cardType 
		--FROM  t_card_national_profiles tcnp, t_techno_on_card_nat_profiles ttocnp, t_technology_types ttt
		--WHERE tcnp.cnpr_id = ttocnp.cnpr_id AND ttocnp.tcty_id = ttt.tcty_id
		--AND tcnp.csfv_id = w_oldSWVersionId;
		
		SELECT ttt.tcty_name
		  INTO w_cardType 
		  FROM t_card_national_profiles tcnp
		  JOIN t_techno_on_card_nat_profiles ttocnp ON tcnp.cnpr_id = ttocnp.cnpr_id
		  JOIN t_technology_types ttt ON ttocnp.tcty_id = ttt.tcty_id
		 WHERE tcnp.csfv_id = w_oldSWVersionId;
 		--BRASIL-440 - fin:
 		--Determiner s'il y aura des modification
 		
 		IF (w_oldCardModel = w_newCardModel AND w_oldCardModId = w_newCardModId AND w_oldSWVersionId = w_newSWVersionId AND w_newSWVersion = w_oldSWVersion AND w_hwVersion = w_oldHwVersion AND w_oldPCPModelNumber = w_newPCPModelNumber 
 			AND w_oldCardModelFamille = w_newCardModelFamille AND w_changePortSpf = w_oldchangePortSpf) 
 		THEN
 				
 			INSERT INTO changeCardModelLogTableErr
			VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, w_newSfpmShortName, w_newSfpmId, w_cardType,
					'WN', 'Aucune modification à faire en base de données', '98');
			 
			CONTINUE;
 		
 		END IF;
		
 		IF (w_cardType = 'FTTH')
		THEN
			-- cas carte FTTH
			w_result := braProc_changeCardModel_FTTH(w_eqptLog,w_chassisNo, w_cardNo,
						w_cardId,w_oldCardModel, w_oldCardModId, w_oldSWVersionId, w_newCardModel,
						w_newCardModId, w_newSWVersion, w_newSWVersionId,w_hwVersion,w_oldHwVersion,
						w_oldPCPModelNumber,w_newPCPModelNumber,w_chassisId,w_oldCardModelFamille ,
						 w_newCardModelFamille,w_oldSWVersion,w_slot_id,w_newSfpmShortName,w_newSfpmId,w_cardType);
						
			IF w_result <> 0
			THEN
				CONTINUE;
			END IF;
			
		ELSIF (w_cardType <> 'FTTH')
		THEN
			-- cas carte XDSL
			w_result := braProc_changeCardModel_XDSL(w_eqptLog,w_chassisNo, w_cardNo,
						w_cardId,w_oldCardModel, w_oldCardModId, w_oldSWVersionId, w_newCardModel,
						w_newCardModId, w_newSWVersion, w_newSWVersionId,w_hwVersion,w_oldHwVersion,
						w_oldPCPModelNumber,w_newPCPModelNumber,w_chassisId,w_oldCardModelFamille,
						w_newCardModelFamille,w_oldSWVersion,w_slot_id, w_newSfpmShortName, w_newSfpmId,w_cardType);
											
			IF w_result <> 0
			THEN
				CONTINUE;
			END IF;
			
		END IF;
				
		IF array_length(w_arrayCahssis, 1) IS NOT NULL THEN
			-- Il existe d?©j?  des couplets (Chassis,premier port)
			RAISE NOTICE 'Il existe déjà  des couplets (Chassis,premier port)';
			FOREACH w_currentChassis SLICE 1 IN ARRAY w_arrayCahssis
			LOOP 
				IF (w_currentChassis[1] = w_chassisId) THEN
					-- Chassis existe ==> On r?©cupere l'id du premier port.
					RAISE NOTICE 'Chassis existe ==> On récupere id du premier port.';
					w_firtPortId := w_currentChassis[2];
					w_existChassis := true;
					EXIT WHEN w_existChassis;
				END IF;
			END LOOP;
		END IF;
		
		IF NOT w_existChassis THEN
			-- Recuperer le numero de la premiere carte dans le chassis
		
		--	Autre Solution
		--	SELECT card_id INTO w_firstCardId
		--	FROM t_cards c, t_slots s
		--	WHERE c.slot_id = s.slot_id AND s.shlf_id = w_chassisId
		--	ORDER BY card_num LIMIT 1
			
		--	SELECT port_id INTO w_firtPortId
		--	FROM t_ports where card_id = w_firstCardId 
		--	ORDER BY port_num LIMIT 1
	
	  		SELECT min(card_num) INTO w_minCardNumber
	  		FROM t_cards c, t_slots s
			WHERE c.slot_id = s.slot_id AND s.shlf_id = w_chassisId;
			
			-- Recuperer le numero du premier port de la premiere carte
			--BRASIL-440 - ini:
			--SELECT min(port_num) INTO w_minPortNumber
	  		--FROM t_cards c, t_slots s, t_ports p
			--WHERE p.card_id = c.card_id AND c.slot_id = s.slot_id 
			--	AND s.shlf_id = w_chassisId AND card_num = w_minCardNumber;
			SELECT MIN(port_num) INTO w_minPortNumber
			  FROM t_cards c
			  JOIN t_ports p ON p.card_id = c.card_id
			  JOIN t_slots s ON c.slot_id = s.slot_id 
			 WHERE s.shlf_id = w_chassisId 
				AND card_num = w_minCardNumber;
			--BRASIL-440 - fin:
			-- Recuperer l'id du premier port de la premiere carte
			--BRASIL-440 - ini:
			--SELECT port_id INTO w_firtPortId
			--FROM t_cards c, t_slots s, t_ports p
			--WHERE p.card_id = c.card_id AND c.slot_id = s.slot_id AND s.shlf_id = w_chassisId 
			--	AND card_num = w_minCardNumber AND port_num = w_minPortNumber;
			SELECT port_id 
			  INTO w_firtPortId
			  FROM t_cards c
			  JOIN t_ports p ON p.card_id = c.card_id 
			  JOIN t_slots s ON c.slot_id = s.slot_id 
			 WHERE s.shlf_id = w_chassisId 
				AND card_num = w_minCardNumber 
				AND port_num = w_minPortNumber;
			--BRASIL-440 - fin:
			-- On enregistre le couplet Chassis, premier port dans l'array
			w_arrayCahssis := array_cat(w_arrayCahssis, ARRAY[w_chassisId,w_firtPortId]);
		end IF;
				
		--
		-- Recuperer la liste des ports de la carte
		--
		OPEN cur_portsToUpdate(w_cardId);
		 
		--
		-- Changer l'etat et le commentaire des anciens ports de la carte 
		-- hormis le premier port de la premiere carte
		--
		LOOP
    		-- fetch chaque ligne du curseur dans le w_portToUpdate
      		FETCH cur_portsToUpdate INTO w_portToUpdateId;
    		-- Sortir si ne reste aucune ligne
      		EXIT WHEN NOT FOUND;
		--
		-- Modifier Module SPF ports uniquement pour FTTH
		--
			IF (w_cardType = 'FTTH') THEN
				SELECT sfpm_id, sfpm_name
				INTO w_newSfpmId, w_sfpmName
				FROM t_sfp_modules m
				WHERE m.sfmp_short_name = w_newSfpmShortName;
				
				UPDATE t_sfp_module_port_assocs
				SET sfpm_id = w_newSfpmId
				WHERE port_id = w_portToUpdateId;
			END IF;
	    		UPDATE t_ports
				SET port_remarks = '',port_out_status = ' ', port_date_plp = null
				WHERE port_id = w_portToUpdateId
				and port_out_status <> 'R';
   		END LOOP;
  
   		-- Fermer le curseur
   		CLOSE cur_portsToUpdate;
   		
		EXCEPTION
			WHEN OTHERS THEN
				INSERT INTO changeCardModelLogTableErr
					VALUES(w_eqptLog, w_chassisNo,w_chassisId, w_cardNo, w_cardId,
					w_oldCardModel,w_oldCardModId, w_oldSWVersion,w_oldSWVersionId,
					w_newCardModel, w_newCardModId,w_newSWVersion, w_newSWVersionId,w_hwVersion,w_newCardModelFamille, 
					w_newSfpmShortName, w_newSfpmId,w_cardType,
					'KO', SQLERRM, SQLSTATE);
				CONTINUE;
	     END;
		
	-- fin FOR
	END LOOP; 
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_acces_xdsl_cas_3;
--/
CREATE FUNCTION braproc_changecardmodel_acces_xdsl_cas_3 (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint, p_newsfpmshortname character, p_newsfpmid bigint, p_cardtype character)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
		  		w_chassisId					BIGINT;
				w_connecteurTrouve			INTEGER;
			
				w_modCarteNb 				INTEGER;
				w_modPortNb 				INTEGER;
				w_modConnecteurNb 			INTEGER;

				w_num_Max					INTEGER;
				w_num_Max_sans_status		INTEGER;
				w_num_Max_avec_status		INTEGER;
				
				w_result	  				INTEGER;
	BEGIN
		--
		-- Recherche des informations du chassis et du slot
		--
		
		 w_chassisId := NULL;
-- BRASIL-440 - ini:
--		SELECT	chassis.shlf_id
--		INTO	w_chassisId
--		FROM	t_shelfs chassis, t_slots s, t_cards c
--		WHERE	c.card_id = p_cardId
--		AND		s.shlf_id = chassis.shlf_id
--		AND 	c.slot_id = s.slot_id
--		AND 	s.slot_id = p_slot_id;

		SELECT chassis.shlf_id
		INTO w_chassisId
		FROM t_cards c 
		JOIN t_slots s ON c.slot_id = s.slot_id
		JOIN t_shelfs chassis ON s.shlf_id = chassis.shlf_id
		WHERE c.card_id = p_cardId
		AND s.slot_id = p_slot_id;

-- BRASIL-440 - fin:
		
		IF	w_chassisId IS NULL
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,null,null,null,
					'WN', 'Cas5: Chassis de rattachement non trouve', '98');
	
			RETURN 1;
		END IF;
		
		--
		-- verefier le nombre des connecteurs desponible dans la carte
		--
		w_connecteurTrouve := 0;
		
		SELECT count(*) 
		INTO w_connecteurTrouve
		FROM t_ports
		WHERE slot_id = p_slot_id
		AND card_id = p_cardId
		AND port_activation_status = 2;
		
		IF	w_connecteurTrouve <> 0
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,null,null,null,
					'WN', 'Carte Xdsl : Ports avec un statut d’activation incorrect', '98');
	
			RETURN 1;
		END IF;
		
		--
		-- recuperation des ports de slot
		--
		
		INSERT INTO changePortTable
		SELECT port_id, port_num, port_activation_status, port_occup_ont, pogr_id, port_out_status 
		FROM t_ports
		WHERE slot_id = p_slot_id
		AND card_id = p_cardId
		AND port_num > p_newPCPModelNumber
		order by port_num limit (p_oldPCPModelNumber - p_newPCPModelNumber);
		
		--
		-- voir s'il y a un port de la carte qui appartient à un groupe de port
		--
		
		IF EXISTS ( SELECT id
			FROM changePortTable
			WHERE pgrp_id IS NOT NULL
		)
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', 'Carte Xdsl : Un des ports ne restant pas dans la carte appartient à un groupe','98');
	
			RETURN 1;
		END IF;	
		
		--
		-- voir s'il y a un port de la carte occupe
		--
		
		IF EXISTS ( SELECT id
			FROM changePortTable
			WHERE port_occup_ont > 0
		)
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille, p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', 'Carte Xdsl : Un des ports ne restant pas dans la carte est occupe','98');
	
			RETURN 1;
		END IF;	
		
		--
		-- voir s'il y a un port de la carte reserve
		--
		
		IF EXISTS ( SELECT id
			FROM changePortTable
			WHERE port_out_status = 'R'
		)
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille, p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', 'Carte Xdsl : Un des ports ne restant pas dans la carte est réservé','98');
	
			RETURN 1;
		END IF;
		
		--
		-- voir si la carte est enregistree dans la table t_d_dslam_xdsl_cards
		--

			
		IF NOT EXISTS (SELECT card_id
			FROM t_d_dslam_xdsl_cards
			WHERE card_id = p_cardId
		)
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion , p_oldCardModelFamille, p_newSfpmShortName,p_newSfpmId,p_cardType,
					'KO', 'Carte Xdsl : Enregistrement non trouve dans la table t_d_dslam_xdsl_cards ???','X13');
	
			RETURN 1;
		END IF;
		
					
		 w_modCarteNb := 0;
		 w_modPortNb = 0;
		
			--
			-- Mise a jour des ports fusionnes devenant shadow ports
			--
			
			UPDATE	t_ports SET	card_id = null, port_activation_status	=	2
			WHERE port_id in ( select id from changePortTable )
			AND port_activation_status = 1;
			
			--
			-- Suppression des ports sans connecteur
			--
			DELETE FROM t_ports 
			WHERE port_id in ( select id from changePortTable ) 
			AND port_activation_status = 0;
			
			--
			-- mise a jour de la carte
			--
			
			UPDATE	t_cards
			SET		
					cmod_id = p_newCardModId,							
					csfv_id = p_newSWVersionId,
					card_creation_time = clock_timestamp()
			WHERE	card_id = p_cardId;
		
		--
		-- ecriture dans la table de log	
		--
		
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,
					p_hwVersion,p_newCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType, 'OK', 'Succes', '99');

			RETURN w_result;											
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_ftth;
--/
CREATE FUNCTION braproc_changecardmodel_ftth (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
	  
	  w_result 			INTEGER;
	  w_resultUpdate 	INTEGER;
	  w_cardType 		CHAR(10);
BEGIN	
	
	w_result := 0;
	
	--
	-- La carte est une carte de type accès 
	--
	
	IF (p_oldHwVersion <> 'X')
	THEN
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,
					'WN', 'Carte FTTH : L ancien modèle de carte ne correspond pas à une carte client', '98');
		 
		RETURN 1;
	END IF;
	
	--
	-- La nouvelle carte est de type accès
	--
	
	IF (p_hwVersion <> 'X')
	THEN
	
	-- hwVersion du type de carte KO
    	INSERT INTO changeCardModelLogTableErr
            VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,
					'WN', 'Carte FTTH : Le nouveau type de carte ne correspond pas à une carte client / le modèle de carte cible ne correspond pas à une carte client','98');	
             	
			RETURN 1;
	END IF;
	
	--
	-- verefier si le nouveau modèle  de carte a la technologie FTTH
	--
		--BRASIL-440 - ini:
		--SELECT ttt.tcty_name 
		--INTO w_cardType 
		--FROM  t_card_national_profiles tcnp, t_techno_on_card_nat_profiles ttocnp, t_technology_types ttt
		--WHERE tcnp.cnpr_id = ttocnp.cnpr_id 
		--AND ttocnp.tcty_id = ttt.tcty_id
		--AND tcnp.csfv_id = p_newSWVersionId;
		
		SELECT ttt.tcty_name 
		  INTO w_cardType 
		  FROM t_card_national_profiles tcnp
		  JOIN t_techno_on_card_nat_profiles ttocnp ON tcnp.cnpr_id = ttocnp.cnpr_id 
		  JOIN t_technology_types ttt ON ttocnp.tcty_id = ttt.tcty_id
		 WHERE tcnp.csfv_id = p_newSWVersionId;
 		--BRASIL-440 - fin:
 		IF (w_cardType <> 'FTTH')
	THEN
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,
					'WN', 'Carte FTTH : Profil national associe au nouveau modèle de carte n a pas la technologie FTTH', '98');
			 
			RETURN 1;
	END IF;
	
	--
	-- Traitement des differents cas
	--
	
	w_resultUpdate := 0;
	IF	p_newPCPModelNumber = p_oldPCPModelNumber
	THEN
	
		--
		--Cas 1 : Carte FTTH de type accès avec le même nombre de ports
		--modification de la carte
		--
		
		w_resultUpdate := braProc_changeCardModel_FTTH_cas_1(p_eqptLog ,p_chassisNo ,p_cardNo ,
					p_cardId,p_oldCardModel, p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
					p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
					p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId ,p_oldCardModelFamille, p_newCardModelFamille ,p_oldSWVersion,true);
		RETURN w_resultUpdate;
	ELSIF (p_newPCPModelNumber > p_oldPCPModelNumber) THEN
		
		w_resultUpdate := braProc_changeCardModel_FTTH_cas_2(p_eqptLog ,p_chassisNo ,p_cardNo ,
					p_cardId , p_oldCardModel ,p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
					p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
					p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId , p_oldCardModelFamille ,p_newCardModelFamille ,p_oldSWVersion,p_slot_id,true);
		RETURN w_resultUpdate;
	ELSE
		--
		-- moins de PCP sur le nouveau type de carte
		--
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,
					'WN', 'Carte FTTH : Nombre de ports inferieur pour le nouveau type de carte /  Nombre de ports inferieur sur le modèle de carte cible', '98');
		
		RETURN 1;
		
	END IF;
	
	RETURN 0;
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_ftth;
--/
CREATE FUNCTION braproc_changecardmodel_ftth (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint, p_newsfpmshortname character, p_newsfpmid bigint, p_cardtype character)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
	  
	  w_result 			INTEGER;
	  w_resultUpdate 	INTEGER;
	  w_cardType 		CHAR(10);
BEGIN	
	
	w_result := 0;
	
	--
	-- La carte est une carte de type accès 
	--
	
	IF (p_oldHwVersion <> 'X')
	THEN
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', 'Carte FTTH : L ancien modèle de carte ne correspond pas à une carte client', '98');
		 
		RETURN 1;
	END IF;
	
	--
	-- La nouvelle carte est de type accès
	--
	
	IF (p_hwVersion <> 'X')
	THEN
	
	-- hwVersion du type de carte KO
    	INSERT INTO changeCardModelLogTableErr
            VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', 'Carte FTTH : Le nouveau type de carte ne correspond pas à une carte client / le modèle de carte cible ne correspond pas à une carte client','98');	
             	
			RETURN 1;
	END IF;
	
	--
	-- verefier si le nouveau modèle  de carte a la technologie FTTH
	--
		--BRASIL-440 - ini:
		--SELECT ttt.tcty_name 
		--INTO w_cardType 
		--FROM  t_card_national_profiles tcnp, t_techno_on_card_nat_profiles ttocnp, t_technology_types ttt
		--WHERE tcnp.cnpr_id = ttocnp.cnpr_id 
		--AND ttocnp.tcty_id = ttt.tcty_id
		--AND tcnp.csfv_id = p_newSWVersionId;
		
		SELECT ttt.tcty_name 
		  INTO w_cardType 
		  FROM t_card_national_profiles tcnp
		  JOIN t_techno_on_card_nat_profiles ttocnp ON tcnp.cnpr_id = ttocnp.cnpr_id 
		  JOIN t_technology_types ttt ON ttocnp.tcty_id = ttt.tcty_id
		 WHERE tcnp.csfv_id = p_newSWVersionId;
 		--BRASIL-440 - fin:
 		IF (w_cardType <> 'FTTH')
	THEN
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,
					'WN', 'Carte FTTH : Profil national associe au nouveau modèle de carte n a pas la technologie FTTH', '98');
			 
			RETURN 1;
	END IF;
	
	--
	-- Traitement des differents cas
	--
	
	w_resultUpdate := 0;
	IF	p_newPCPModelNumber = p_oldPCPModelNumber
	THEN
	
		--
		--Cas 1 : Carte FTTH de type accès avec le même nombre de ports
		--modification de la carte
		--
		
		w_resultUpdate := braProc_changeCardModel_FTTH_cas_1(p_eqptLog ,p_chassisNo ,p_cardNo ,
					p_cardId,p_oldCardModel, p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
					p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
					p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId ,
					p_oldCardModelFamille, p_newCardModelFamille ,p_oldSWVersion,true,
					p_newSfpmShortName,p_newSfpmId,p_cardType);
		RETURN w_resultUpdate;
	ELSIF (p_newPCPModelNumber > p_oldPCPModelNumber) THEN
		
		w_resultUpdate := braProc_changeCardModel_FTTH_cas_2(p_eqptLog ,p_chassisNo ,p_cardNo ,
					p_cardId , p_oldCardModel ,p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
					p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
					p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId , 
					p_oldCardModelFamille ,p_newCardModelFamille ,p_oldSWVersion,p_slot_id,true,
					p_newSfpmShortName,p_newSfpmId,p_cardType);
		RETURN w_resultUpdate;
	ELSE
		--
		-- moins de PCP sur le nouveau type de carte
		--
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', 'Carte FTTH : Nombre de ports inferieur pour le nouveau type de carte /  Nombre de ports inferieur sur le modèle de carte cible', '98');
		
		RETURN 1;
		
	END IF;
	
	RETURN 0;
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_ftth_cas_1;
--/
CREATE FUNCTION braproc_changecardmodel_ftth_cas_1 (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, isftth boolean)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
		w_modifiedEquipNumber		INTEGER;	
		w_result	  				INTEGER;
		w_nbrNetPortModel			INTEGER;
BEGIN
			
	IF ( NOT(isFTTH) AND p_hwVersion = 'R')
	THEN
		
		w_nbrNetPortModel := 0;
	
		--
		-- Verifier que les types de ports sont identiques entre l ancienne et la nouvelle carte
		--
		
		--BRASIL-440 - ini:
		--SELECT	SUM(tnp.npmd_port_size) 
		--INTO	w_nbrNetPortModel
		--FROM t_net_port_models tnp,t_net_port_models tnp1
		--WHERE tnp.cmod_id = p_oldCardModId
		--AND tnp1.cmod_id = p_newCardModId
		--AND tnp1.npmd_port_type = tnp.npmd_port_type;
		SELECT	SUM(tnp.npmd_port_size) 
		  INTO	w_nbrNetPortModel
		  FROM t_net_port_models tnp
		  JOIN t_net_port_models tnp1 ON tnp1.npmd_port_type = tnp.npmd_port_type
		 WHERE tnp.cmod_id = p_oldCardModId
		   AND tnp1.cmod_id = p_newCardModId;
		--BRASIL-440 - fin:
		IF( p_newPCPModelNumber IS DISTINCT FROM  w_nbrNetPortModel )
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,
					'WN', 'Carte Xdsl : Les types des ports de la nouvelle carte ne correspondent pas aux anciens ports / Les types des ports de la carte cible ne correspondent pas aux anciens ports', '98');
			RETURN 1;
		END IF;
	
	END IF;
	
		--
		-- mise a jour de la carte
		--
		
		UPDATE	t_cards SET cmod_id = p_newCardModId, csfv_id = p_newSWVersionId, card_creation_time = clock_timestamp() WHERE card_id = p_cardId;
	
	IF( w_result <> 0)
	THEN
		RETURN 1;
	END IF;
	
	--
	-- ecriture dans la table de log	
	--
	
	INSERT INTO changeCardModelLogTableErr
	VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_hwVersion,p_newCardModelFamille, 'OK', 'Succes', 99);
		
		RETURN 0;														
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_ftth_cas_1;
--/
CREATE FUNCTION braproc_changecardmodel_ftth_cas_1 (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, isftth boolean, p_newsfpmshortname character, p_newsfpmid bigint, p_cardtype character)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
		w_modifiedEquipNumber		INTEGER;	
		w_result	  				INTEGER;
		w_nbrNetPortModel			INTEGER;
BEGIN
			
	IF ( NOT(isFTTH) AND p_hwVersion = 'R')
	THEN
		
		w_nbrNetPortModel := 0;
	
		--
		-- Verifier que les types de ports sont identiques entre l ancienne et la nouvelle carte
		--
		
		--BRASIL-440 - ini:
		--SELECT	SUM(tnp.npmd_port_size) 
		--INTO	w_nbrNetPortModel
		--FROM t_net_port_models tnp,t_net_port_models tnp1
		--WHERE tnp.cmod_id = p_oldCardModId
		--AND tnp1.cmod_id = p_newCardModId
		--AND tnp1.npmd_port_type = tnp.npmd_port_type;
		SELECT	SUM(tnp.npmd_port_size) 
		  INTO	w_nbrNetPortModel
		  FROM t_net_port_models tnp
		  JOIN t_net_port_models tnp1 ON tnp1.npmd_port_type = tnp.npmd_port_type
		 WHERE tnp.cmod_id = p_oldCardModId
		   AND tnp1.cmod_id = p_newCardModId;
		--BRASIL-440 - fin:
		IF( p_newPCPModelNumber IS DISTINCT FROM  w_nbrNetPortModel )
		THEN
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', 'Carte Xdsl : Les types des ports de la nouvelle carte ne correspondent pas aux anciens ports / Les types des ports de la carte cible ne correspondent pas aux anciens ports', '98');
			RETURN 1;
		END IF;
	
	END IF;
	
		--
		-- mise a jour de la carte
		--
		
		UPDATE	t_cards SET cmod_id = p_newCardModId, csfv_id = p_newSWVersionId, card_creation_time = clock_timestamp() WHERE card_id = p_cardId;
	
	IF( w_result <> 0)
	THEN
		RETURN 1;
	END IF;
	
	--
	-- ecriture dans la table de log	
	--
	
	INSERT INTO changeCardModelLogTableErr
	VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_hwVersion,
					p_newCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType, 'OK', 'Succes', '99');
		
		RETURN 0;														
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_ftth_cas_2;
--/
CREATE FUNCTION braproc_changecardmodel_ftth_cas_2 (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint, isftth boolean)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
				w_connecteurTrouve			INTEGER;
			
				w_modCarteNb 				INTEGER;
				w_modPortNb 				INTEGER;
				w_modConnecteurNb 			INTEGER;

				w_num_Max					INTEGER;
				w_num_Max_sans_status		INTEGER;
				w_num_Max_avec_status		INTEGER;
				w_result					INTEGER;
				errMessage 					CHAR(100);
				errCode						CHAR(20);
	BEGIN
		
		--
		-- max de num Por de cart 
		--
		
		w_num_Max := 0;
		
		SELECT max(port_num)
		INTO w_num_Max
		FROM t_ports
		WHERE card_id = p_cardId;
		
		--
		-- verefier le nombre des connecteurs desponible dans le slot
		--
		w_connecteurTrouve := 0;
		
		SELECT count(*) FROM t_ports
		INTO w_connecteurTrouve
		WHERE slot_id = p_slot_id
		AND card_id is null
		AND port_num > w_num_Max
		AND port_activation_status = 2;
		
		IF	w_connecteurTrouve < ( p_newPCPModelNumber - p_oldPCPModelNumber )
		THEN
		
			IF isFTTH THEN
					errMessage := 'Carte FTTH :Carte cible non autorisée dans ce chassis';
					errCode := '98';
			ELSIF (p_hwVersion = 'R')
				THEN				
					errMessage := 'Cas 7 : Connecteur(s) manquant(s) dans le slot';
					errCode := '98';
			 ELSE
			 		errMessage := 'Carte Xdsl :Carte cible non autorisée dans ce chassis';
					errCode := '98';
			END IF;
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId, p_oldHwVersion ,p_oldCardModelFamille,
					'WN', errMessage, errCode);
			
			 
			RETURN 1;
		END IF;
		
		--
		--recuperation des ports de slot
		--
		
		INSERT INTO changePortTable (id,num,status)
		SELECT port_id, port_num, port_activation_status 
		FROM t_ports
		WHERE slot_id = p_slot_id
		AND card_id is null
		AND port_activation_status = 2
		AND port_num > w_num_Max
		order by port_num limit (p_newPCPModelNumber - p_oldPCPModelNumber);
		
		--
		-- voir si Les numéros de port de la carte sont contigus
		--
		
		IF EXISTS ( SELECT	num
			FROM	changePortTable
			WHERE	num < w_num_Max )
		THEN
			IF isFTTH THEN
				errMessage := 'Cas7: Les numéros des ports ne sont pas contigus';
			END IF;
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,
					'WN', errMessage,'98');
			 
			RETURN 1;
		END IF;			
		
		--
		-- recuperation de max des ports de slot sans filter avec status (port_activation_status) 
		--
		
		select max(port_num) 
		INTO w_num_Max_sans_status
		from t_ports  where slot_id = p_slot_id 
		AND port_num > w_num_Max
		limit (p_newPCPModelNumber - p_oldPCPModelNumber);
		
		--
		-- recuperation de max des ports de slot avec filter avec status (port_activation_status) 
		--
		
		select max(port_num) 
		INTO w_num_Max_avec_status
		from t_ports  where slot_id = p_slot_id 
		AND port_activation_status = 2
		AND port_num > w_num_Max
		limit (p_newPCPModelNumber - p_oldPCPModelNumber);
		
		--
		-- comparaison des 2 max  
		--
		
		IF w_num_Max_sans_status <> w_num_Max_avec_status
		THEN
		
			IF isFTTH THEN
				errMessage := 'Cas7: Les numéros des ports ne sont pas contigus';
			END IF;
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,
					'WN', errMessage,'98');
			 
			RETURN 1;
		END IF;
					
		 w_modCarteNb := 0;
		 w_modPortNb := 0;
					
			--
			-- Mise a jour des shadow ports devenant ports fusionnes
			--
			
			UPDATE	t_ports SET	card_id = p_cardId, 
			port_activation_status	=	1
			WHERE port_id in ( select id from changePortTable ); 								
			
			GET DIAGNOSTICS w_modPortNb = ROW_COUNT;
			
			--
			-- mise a jour de la carte
			--
			
			UPDATE	t_cards
			SET		
					cmod_id = p_newCardModId,							
					csfv_id = p_newSWVersionId,
					card_creation_time = clock_timestamp()
			WHERE	card_id = p_cardId;
			
			GET DIAGNOSTICS w_modCarteNb = ROW_COUNT;
		
		--
		-- ecriture dans la table de log	
		--
		
		IF isFTTH THEN
					errMessage := 'Cas2';
		ELSIF (p_hwVersion = 'R')
			THEN				
				errMessage := 'Cas 7';
		 ELSE
		 		errMessage := 'Cas 4';
		END IF;
		
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_hwVersion,p_newCardModelFamille, 'OK', 'Succes', '99');
		
		IF( w_result <> 0)
		THEN
			RETURN 1;
		END IF;
		   		
		RETURN 0;											
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_ftth_cas_2;
--/
CREATE FUNCTION braproc_changecardmodel_ftth_cas_2 (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint, isftth boolean, p_newsfpmshortname character, p_newsfpmid bigint, p_cardtype character)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
				w_connecteurTrouve			INTEGER;
			
				w_modCarteNb 				INTEGER;
				w_modPortNb 				INTEGER;
				w_modConnecteurNb 			INTEGER;

				w_num_Max					INTEGER;
				w_num_Max_sans_status		INTEGER;
				w_num_Max_avec_status		INTEGER;
				w_result					INTEGER;
				errMessage 					CHAR(100);
				errCode						CHAR(20);
	BEGIN
		
		--
		-- max de num Por de cart 
		--
		
		w_num_Max := 0;
		
		SELECT max(port_num)
		INTO w_num_Max
		FROM t_ports
		WHERE card_id = p_cardId;
		
		--
		-- verefier le nombre des connecteurs desponible dans le slot
		--
		w_connecteurTrouve := 0;
		
		SELECT count(*) FROM t_ports
		INTO w_connecteurTrouve
		WHERE slot_id = p_slot_id
		AND card_id is null
		AND port_num > w_num_Max
		AND port_activation_status = 2;
		
		IF	w_connecteurTrouve < ( p_newPCPModelNumber - p_oldPCPModelNumber )
		THEN
		
			IF isFTTH THEN
					errMessage := 'Carte FTTH :Carte cible non autorisée dans ce chassis';
					errCode := '98';
			ELSIF (p_hwVersion = 'R')
				THEN				
					errMessage := 'Cas 7 : Connecteur(s) manquant(s) dans le slot';
					errCode := '98';
			 ELSE
			 		errMessage := 'Carte Xdsl :Carte cible non autorisée dans ce chassis';
					errCode := '98';
			END IF;
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId, p_oldHwVersion ,p_oldCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', errMessage, errCode);
			
			 
			RETURN 1;
		END IF;
		
		--
		--recuperation des ports de slot
		--
		
		INSERT INTO changePortTable (id,num,status)
		SELECT port_id, port_num, port_activation_status 
		FROM t_ports
		WHERE slot_id = p_slot_id
		AND card_id is null
		AND port_activation_status = 2
		AND port_num > w_num_Max
		order by port_num limit (p_newPCPModelNumber - p_oldPCPModelNumber);
		
		--
		-- voir si Les numéros de port de la carte sont contigus
		--
		
		IF EXISTS ( SELECT	num
			FROM	changePortTable
			WHERE	num < w_num_Max )
		THEN
			IF isFTTH THEN
				errMessage := 'Cas7: Les numéros des ports ne sont pas contigus';
			END IF;
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', errMessage,'98');
			 
			RETURN 1;
		END IF;			
		
		--
		-- recuperation de max des ports de slot sans filter avec status (port_activation_status) 
		--
		
		select max(port_num) 
		INTO w_num_Max_sans_status
		from t_ports  where slot_id = p_slot_id 
		AND port_num > w_num_Max
		limit (p_newPCPModelNumber - p_oldPCPModelNumber);
		
		--
		-- recuperation de max des ports de slot avec filter avec status (port_activation_status) 
		--
		
		select max(port_num) 
		INTO w_num_Max_avec_status
		from t_ports  where slot_id = p_slot_id 
		AND port_activation_status = 2
		AND port_num > w_num_Max
		limit (p_newPCPModelNumber - p_oldPCPModelNumber);
		
		--
		-- comparaison des 2 max  
		--
		
		IF w_num_Max_sans_status <> w_num_Max_avec_status
		THEN
		
			IF isFTTH THEN
				errMessage := 'Cas7: Les numéros des ports ne sont pas contigus';
			END IF;
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille, p_newSfpmShortName,p_newSfpmId,p_cardType,
					'WN', errMessage,'98');
			 
			RETURN 1;
		END IF;
					
		 w_modCarteNb := 0;
		 w_modPortNb := 0;
					
			--
			-- Mise a jour des shadow ports devenant ports fusionnes
			--
			
			UPDATE	t_ports SET	card_id = p_cardId, 
			port_activation_status	=	1
			WHERE port_id in ( select id from changePortTable ); 								
			
			GET DIAGNOSTICS w_modPortNb = ROW_COUNT;

			--
			-- mise a jour de la carte
			--
			
			UPDATE	t_cards
			SET		
					cmod_id = p_newCardModId,							
					csfv_id = p_newSWVersionId,
					card_creation_time = clock_timestamp()
			WHERE	card_id = p_cardId;
			
			GET DIAGNOSTICS w_modCarteNb = ROW_COUNT;
	
		--
		-- ecriture dans la table de log	
		--
		
		IF isFTTH THEN
					errMessage := 'Cas2';
		ELSIF (p_hwVersion = 'R')
			THEN				
				errMessage := 'Cas 7';
		 ELSE
		 		errMessage := 'Cas 4';
		END IF;
		
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_hwVersion,
					p_newCardModelFamille,p_newSfpmShortName,p_newSfpmId,p_cardType, 'OK', 'Succes', '99');
		
		IF( w_result <> 0)
		THEN
			RETURN 1;
		END IF;
		   		
		RETURN 0;											
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_xdsl;
--/
CREATE FUNCTION braproc_changecardmodel_xdsl (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint, p_newsfpmshortname character, p_newsfpmid bigint, p_cardtype character)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
	  
	  w_resultUpdate 	INTEGER;
	  w_cardType 		CHAR(10);
	  
BEGIN	
	
	--
	-- verifier si le nouveau modèle de carte a la technologie XDSL
	--
		--BRASIL-440 - ini:
	    --SELECT ttt.tcty_name 
		--INTO w_cardType 
		--FROM  t_card_national_profiles tcnp, t_techno_on_card_nat_profiles ttocnp, t_technology_types ttt
		--WHERE tcnp.cnpr_id = ttocnp.cnpr_id AND ttocnp.tcty_id = ttt.tcty_id
		--AND tcnp.csfv_id = p_newSWVersionId;
		
		SELECT ttt.tcty_name 
		  INTO w_cardType 
		  FROM t_card_national_profiles tcnp
		  JOIN t_techno_on_card_nat_profiles ttocnp ON tcnp.cnpr_id = ttocnp.cnpr_id
		  JOIN t_technology_types ttt ON ttocnp.tcty_id = ttt.tcty_id
		 WHERE tcnp.csfv_id = p_newSWVersionId;
	    --BRASIL-440 - fin:
 
 		IF (w_cardType = 'FTTH')
	THEN
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,null,null,null,
					'WN', 'Carte Xdsl : Nouveau modèle de carte de type FTTH / modèle de carte cible de type FTTH ', '98');
		RETURN 1;
	END IF;
	
	--
	-- La carte est une carte de type accès et La nouvelle carte est de type different
	--
	
	IF (p_oldHwVersion = 'X' AND p_hwVersion <> 'X')
	THEN
		INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,null,null,null,
					'WN', 'Carte Xdsl de type Accès : Le nouveau type de carte ne correspond pas à une carte client / Le modèle de carte cible ne correspond pas à une carte client', '98');

		RETURN 1;
	END IF;
	
	--
	-- La carte est une carte de type different du type accès et La nouvelle carte est de type accès
	--
	
	IF (p_oldHwVersion <> 'X' AND p_hwVersion = 'X')
	THEN
	
	-- hwVersion du type de carte KO
    	INSERT INTO changeCardModelLogTableErr
            VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,null,null,null,
					'WN', 'Carte Xdsl : de type collecte : Le nouveau type de carte ne correspond pas à une carte réseau', '98');		
			RETURN 1;
	END IF;
	
	--
	-- Traitement des differents cas
	--
	
	w_resultUpdate := 0;
	IF(p_oldHwVersion = 'X')
	THEN
		IF	(p_newPCPModelNumber = p_oldPCPModelNumber)
		THEN
			--
			--Cas 3 : Carte XDSL de type accès avec le même nombre de ports
			--modification de la carte
			--
			
			w_resultUpdate := braProc_changeCardModel_FTTH_cas_1(p_eqptLog ,p_chassisNo ,p_cardNo ,
					p_cardId,p_oldCardModel, p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
					p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
					p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId ,p_oldCardModelFamille ,p_newCardModelFamille,p_oldSWVersion,false,p_newSfpmShortName,p_newSfpmId,p_cardType);
			RETURN w_resultUpdate;
		ELSIF (p_newPCPModelNumber > p_oldPCPModelNumber) THEN
			--
			--Cas 4 : Carte XDSL de type accès avec nombre de ports superieur
			--modification de la carte
			--
			
			w_resultUpdate := braProc_changeCardModel_FTTH_cas_2(p_eqptLog ,p_chassisNo ,p_cardNo ,
					p_cardId , p_oldCardModel ,p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
					p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
					p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId ,p_oldCardModelFamille,p_newCardModelFamille,p_oldSWVersion,p_slot_id,false,p_newSfpmShortName,p_newSfpmId,p_cardType);
			RETURN w_resultUpdate;
		ELSE
			--
			--Cas 5 : Carte XDSL de type accès avec nombre de ports inferieur
			--modification de la carte
			--
			
			w_resultUpdate := braProc_changeCardModel_ACCES_XDSL_cas_3(p_eqptLog ,p_chassisNo ,p_cardNo ,
						p_cardId , p_oldCardModel ,p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
						p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
						p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId ,p_oldCardModelFamille,p_newCardModelFamille ,p_oldSWVersion,p_slot_id );
			RETURN w_resultUpdate;
			
		END IF;
		
	ELSIF(p_oldHwVersion <> 'X')
	THEN
		w_resultUpdate := braProc_changeCardModel_XDSL_RESEAU(p_eqptLog ,p_chassisNo ,p_cardNo ,
						p_cardId , p_oldCardModel ,p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
						p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
						p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId ,p_oldCardModelFamille,p_newCardModelFamille ,p_oldSWVersion,p_slot_id, p_newSfpmShortName, p_newSfpmId,p_cardType);
		RETURN w_resultUpdate;
	END IF;
	
	RETURN 0;
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_xdsl_cas_7;
--/
CREATE FUNCTION braproc_changecardmodel_xdsl_cas_7 (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
		cabledStripeId 			INTEGER;
		freePortsNbr 			INTEGER;
		notCabledPortsNbr 		INTEGER;
		cardLastPort 			INTEGER;
 		stripeLastBroche 		INTEGER;
 		intervale				INTEGER;
 		w_ligne  				RECORD;
 		portToCable				RECORD;
 		w_modCarteNb			INTEGER;
 		w_modPortNb				INTEGER;
 		w_portPinNum			INTEGER;
 		exist					INTEGER;
 		w_result				INTEGER;
 		w_num_Max				INTEGER;
BEGIN
		
		w_num_Max := 0;
		
		SELECT max(port_num)
		INTO w_num_Max
		FROM t_ports
		WHERE card_id = p_cardId;
		
		--
		-- recuperation de l ID du réglette
		--
		
		SELECT DISTINCT strp_id
		INTO cabledStripeId
		FROM t_ports
		WHERE card_id = p_cardId;
		
		--
		-- recuperation de nombre de broche libre dans la réglette
		--
		
		SELECT strp_free_pin_count
		INTO  freePortsNbr
		FROM t_stripes
		WHERE strp_id = cabledStripeId;
		
		--
		-- Recuperer le nombre de ports non cable de la carte
		--
		
		SELECT count(*)
		INTO notCabledPortsNbr
		FROM t_ports
		WHERE slot_id = p_slot_id
		AND port_num > w_num_Max
		AND port_activation_status = 2;
		
		--
		-- voir si le nombre des ports libre est insuffisant
		--
		
		IF	( (p_newPCPModelNumber - p_oldPCPModelNumber) <= freePortsNbr AND (p_newPCPModelNumber - p_oldPCPModelNumber) <= notCabledPortsNbr)
		THEN			
			
			--
			-- recuperation des nouveux ports libre pour l insertion
			--
			
			INSERT INTO changePortTable (id,num)
		    SELECT port_id,port_num 
			FROM t_ports
			WHERE port_activation_status = 2
			AND slot_id = p_slot_id
			AND port_num > w_num_Max
			order by port_num
			limit (p_newPCPModelNumber - p_oldPCPModelNumber);			
			
			--On recupere le dernier port cable de la carte et de la réglette
			SELECT MAX (port_num) INTO cardLastPort  FROM t_ports WHERE card_id=p_cardId and strp_id = cabledStripeId;
			SELECT MAX (port_pin_num) INTO stripeLastBroche FROM t_ports WHERE card_id = p_cardId and strp_id = cabledStripeId;
			
			intervale = cardLastPort - stripeLastBroche;
			
			--
			-- Pour chaque Port libre ....
			--
			
			FOR portToCable IN SELECT id,num FROM changePortTable
	  		LOOP
	  		  --On Verifie si la broche correspondante n est pas deja cablee
				select  count(port_id) into exist  from t_ports where port_activation_status = 0 and strp_id = cabledStripeId and port_pin_num = (portToCable.num - intervale);
				IF exist = 1
				THEN
					INSERT INTO changeCardModelLogTableErr
						VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion, p_oldCardModelFamille,null,null,null,
					'WN','Carte Xdsl : Les numéros de broches de la réglette ne sont pas contigus.', '98');					
					RETURN 1;
				END IF;
	  		END LOOP;
										
			w_modCarteNb := 0;
		 	w_modPortNb := 0;
			
				--
				-- Pour chaque Port libre ....
				--
				
				FOR portToCable IN SELECT * FROM changePortTable
		  		LOOP
		  			--- le numéro correspondant
		  			w_portPinNum := portToCable.num - intervale;
		  			
					--insertion

					INSERT INTO t_ports ( port_num , port_type , port_pin_num , port_occup_status , port_occup_ont, port_occupation_status, 
										  port_activation_status, port_prod_status , port_attribuable, card_id , slot_id , strp_id)
					values ( portToCable.num , 'R', w_portPinNum , 0 , 0 , 0 ,0 , 'O', 1 , p_cardId , p_slot_id , cabledStripeId );

					-- update pour détourner les changements fait par le trigger lancé lors de l'insertion d'un nouveau port

                    UPDATE t_ports set port_type = 'R', port_pin_num = w_portPinNum, port_occup_status = 0, port_occup_ont = 0, port_occupation_status = 0, 
									   port_activation_status = 0, port_prod_status  = 'O', port_attribuable = 1, slot_id = p_slot_id, strp_id = cabledStripeId 
					where card_id = p_cardId and port_num = portToCable.num;


		  			w_modPortNb := w_modPortNb + 1;
		  					  			
				-- fin FOR
				END LOOP;
			
				--
				-- mise a jour de la carte
				--
				
				UPDATE	t_cards
				SET		
						cmod_id = p_newCardModId,							
						csfv_id = p_newSWVersionId,
						card_creation_time = clock_timestamp()
				WHERE	card_id = p_cardId;
				
				GET DIAGNOSTICS w_modCarteNb = ROW_COUNT;
									
			
			--
			-- ecriture dans la table de log	
			--
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,
					p_hwVersion,p_newCardModelFamille,null,null,null,'OK', 'Succes', '99');
			
			IF( w_result <> 0)
			THEN
				RETURN 1;
			END IF;
			
			
		ELSE
			
			--
			-- nombre de port insuffisant dans la réglette
			--
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_hwVersion,p_newCardModelFamille,null,null,null,
					'WN','Carte Xdsl :Nombre de ports insuffisant dans la réglette,', '98');
			RETURN 1;
		END IF;		
	
	RETURN 0;														
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_xdsl_cas_8;
--/
CREATE FUNCTION braproc_changecardmodel_xdsl_cas_8 (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
 		w_result				INTEGER;
 		w_num_Max				INTEGER;
BEGIN
		
			w_num_Max := 0;
			
			SELECT max(port_num)
			INTO w_num_Max
			FROM t_ports
			WHERE card_id = p_cardId;
					
			--
			-- insertion des port ....
			--
		
			FOR portToCable IN 1 .. (p_newPCPModelNumber - p_oldPCPModelNumber)
	  		LOOP
	  			--- le numéro correspondant
	  			w_num_Max := w_num_Max + 1;
	  			
	  			--insertion
	  			INSERT INTO t_ports ( port_num , port_type , port_occup_status , port_occup_ont, port_occupation_status, 
	  								port_activation_status, port_prod_status , port_attribuable, card_id , slot_id )
	  						 values ( w_num_Max , 'R' , 0 , 0 , 0 ,0 , 'O' , 1 , p_cardId , p_slot_id );
	  						 
	  			-- update pour détourner les changements fait par le trigger lancé lors de l'insertion d'un nouveau port		  			
	  			UPDATE t_ports SET port_attribuable = 1 WHERE card_id = p_cardId AND port_num = w_num_Max;
			-- fin FOR
			END LOOP;
		
			--
			-- mise a jour de la carte
			--
			
			UPDATE	t_cards
			SET		
					cmod_id = p_newCardModId,							
					csfv_id = p_newSWVersionId,
					card_creation_time = clock_timestamp()
			WHERE	card_id = p_cardId;
			
			--
			-- ecriture dans la table de log	
			--
			
			INSERT INTO changeCardModelLogTableErr
			VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,
					p_hwVersion,p_newCardModelFamille,null,null,null, 'OK', 'Succes', '99');
			
			IF( w_result <> 0)
			THEN
				RETURN 1;
			END IF;
				
	RETURN 0;														
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changecardmodel_xdsl_reseau;
--/
CREATE FUNCTION braproc_changecardmodel_xdsl_reseau (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_oldcardmodelfamille character, p_newcardmodelfamille character, p_oldswversion character, p_slot_id bigint, p_newsfpmshortname character, p_newsfpmid bigint, p_cardtype character)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
		w_cabledStripesNbr 	INTEGER;
		w_resultUpdate		INTEGER;
BEGIN
	
	IF( p_newPCPModelNumber < p_oldPCPModelNumber )
	THEN		
		
		--
		-- Nombre de ports inferieur pour le nouveau type de carte
		--
		
		INSERT INTO changeCardModelLogTableErr
					VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,null,null,null,
					'WN', 'Carte Xdsl : de type collecte : Nombre de ports inferieur pour le nouveau type de carte / Nombre de ports inferieur pour le modèle de carte cible', '98');	
		RETURN 1;
	ELSIF ( p_newPCPModelNumber = p_oldPCPModelNumber) THEN
		
		--
		-- même nombre de ports 
		--
		
		w_resultUpdate := braProc_changeCardModel_FTTH_cas_1(p_eqptLog ,p_chassisNo ,p_cardNo ,
					p_cardId,p_oldCardModel, p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
					p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
					p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId ,
					p_oldCardModelFamille,p_newCardModelFamille ,p_oldSWVersion,false,
					p_newSfpmShortName,p_newSfpmId,p_cardType);
		RETURN w_resultUpdate;
		
	ELSE
		
		--
		-- Nombre de ports superieur
		--
		
		--
		-- calcule de nombre des réglettes
		--
				
		SELECT count(DISTINCT strp_id) 
		INTO w_cabledStripesNbr
		FROM t_ports
		WHERE card_id = p_cardId
		AND strp_id is not null;
				
		IF( w_cabledStripesNbr > 1 )
		THEN		
			
			--
			-- Cas 7 : La carte a plusieurs reglettes
			--
			
			INSERT INTO changeCardModelLogTableErr
				VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_oldHwVersion,p_oldCardModelFamille,null,null,null,
					'WN','Carte Xdsl : La carte a plusieurs réglettes', '98');		
			
			RETURN 1;
		
		ELSIF ( w_cabledStripesNbr = 1) THEN
			
			--
			-- Cas 7 : La carte a une réglette
			--
			
			 w_resultUpdate = braProc_changeCardModel_XDSL_cas_7(p_eqptLog,p_chassisNo ,p_cardNo ,
						p_cardId , p_oldCardModel ,p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
						p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
						p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId ,p_oldCardModelFamille,
						p_newCardModelFamille ,p_oldSWVersion,p_slot_id);
			RETURN w_resultUpdate;		
		ELSE
		
			--
			-- la carte sans réglette
			--
			
			w_resultUpdate := braProc_changeCardModel_XDSL_cas_8(p_eqptLog ,p_chassisNo ,p_cardNo ,
						p_cardId , p_oldCardModel ,p_oldCardModId ,p_oldSWVersionId ,p_newCardModel ,
						p_newCardModId ,p_newSWVersion ,p_newSWVersionId ,p_hwVersion ,
						p_oldHwVersion ,p_oldPCPModelNumber ,p_newPCPModelNumber ,p_chassisId,p_oldCardModelFamille ,p_newCardModelFamille ,p_oldSWVersion,p_slot_id);
			RETURN w_resultUpdate;
		
		END IF;
	END IF;
RETURN 0;														
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_changeetatprod;
--/
CREATE FUNCTION braproc_changeetatprod (ligne text)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 
	w_ligne  				RECORD;
	w_split_ligne	TEXT[];
	w_id_objet BIGINT;
	w_typeObjet CHAR(1);
	w_is_controles_ok BOOLEAN:=true;
	w_remark_length INT;
		
BEGIN
	w_split_ligne = string_to_array(ligne, '|');
		
	IF(braProc_checkLineFormat(ligne, w_split_ligne) AND braProc_checkFormatTypeObjet(ligne, w_split_ligne))  THEN
		w_typeObjet := w_split_ligne[1];
		
		IF(w_typeObjet = 'D') THEN
			w_is_controles_ok := braProc_checkDslamName(ligne, w_split_ligne);
			w_remark_length:=255;
		ELSIF(w_typeObjet = 'S') THEN
			w_is_controles_ok := braProc_checkDslamName(ligne, w_split_ligne) AND braProc_checkChassisNum(ligne, w_split_ligne);
			w_remark_length:=128;
		ELSIF(w_typeObjet = 'C') THEN
			w_is_controles_ok := braProc_checkDslamName(ligne, w_split_ligne) AND braProc_checkChassisNum(ligne, w_split_ligne)
								 AND braProc_checkCardNum(ligne, w_split_ligne);
			w_remark_length :=128;
		ELSIF(w_typeObjet = 'P') THEN
			w_is_controles_ok := braProc_checkDslamName(ligne, w_split_ligne) AND braProc_checkChassisNum(ligne, w_split_ligne)
								 AND braProc_checkCardNum(ligne, w_split_ligne) AND braProc_checkPortNum(ligne, w_split_ligne);
			w_remark_length :=255;
		END IF;
		
		w_is_controles_ok := w_is_controles_ok AND braProc_checkFormatEtatProduction(ligne, w_split_ligne) AND braProc_checkFormatSupprimerCommentaire(ligne, w_split_ligne);
		
		-- Si les contrôles précedents sont OK, on vérifie l'existance du DSLAM					 
		IF(w_is_controles_ok) THEN
			w_id_objet := braProc_checkDslamExist(ligne, w_split_ligne);
			w_is_controles_ok := w_is_controles_ok AND w_id_objet IS NOT NULL;
			
			-- Si le DSLAM existe, on vérifie l'existance du chassis
			IF(w_is_controles_ok AND (w_typeObjet = 'S' OR w_typeObjet = 'C' OR w_typeObjet = 'P')) THEN
				w_id_objet := braProc_checkChassisExist(ligne, w_split_ligne, w_id_objet);
				w_is_controles_ok := w_is_controles_ok AND w_id_objet IS NOT NULL;
				
				-- Si le Chassis existe, on vérifie l'existance de la carte
				IF(w_is_controles_ok AND (w_typeObjet = 'C' OR w_typeObjet = 'P')) THEN
					w_id_objet := braProc_checkCarteExist(ligne, w_split_ligne, w_id_objet);
					w_is_controles_ok := w_is_controles_ok AND w_id_objet IS NOT NULL;
					
					-- Si le Carte existe, on vérifie l'existance du port
					IF(w_is_controles_ok AND w_typeObjet = 'P') THEN
						w_id_objet := braProc_checkPortExist(ligne, w_split_ligne, w_id_objet);
						w_is_controles_ok := w_is_controles_ok AND w_id_objet IS NOT NULL;
					END IF;
				END IF;
			END IF;
		END IF;
		
		-- Si les contrôles sont OK, on lance la mise à jour
		IF(w_is_controles_ok AND braProc_checkRemarkLength(ligne, w_id_objet, w_split_ligne, w_remark_length)) THEN
			PERFORM braProc_miseAjourObjet(ligne, w_id_objet, w_split_ligne);
		END IF;
	END IF;

EXCEPTION WHEN OTHERS THEN
	INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(ligne, 'KO', SQLERRM, SQLSTATE);	
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkcardnum;
--/
CREATE FUNCTION braproc_checkcardnum (p_ligne text, p_split_ligne text[])  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_num_carte VARCHAR;
BEGIN
	w_num_carte := p_split_ligne[4];
	IF (braProc_isnumeric(w_num_carte) = false) THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Format de la carte incorrect', '5');	
		isOK := FALSE;
	END IF;
	RETURN isOK;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkcarteexist;
--/
CREATE FUNCTION braproc_checkcarteexist (p_ligne text, p_split_ligne text[], p_chassis_id bigint)  RETURNS bigint
  VOLATILE
AS $dbvis$
DECLARE 
	w_nomDslam VARCHAR;
	w_num_chassis NUMERIC;
	w_num_carte NUMERIC;
	w_idCarte BIGINT;
		
BEGIN
	
	w_nomDslam := p_split_ligne[2];
	w_num_chassis := p_split_ligne[3]::NUMERIC;
	w_num_carte := p_split_ligne[4]::NUMERIC;
	
	SELECT card_id INTO w_idCarte FROM t_cards NATURAL JOIN t_slots  WHERE card_num = w_num_carte AND shlf_id = p_chassis_id;
	IF NOT FOUND THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'WN', 'Carte inexistante sur le chassis '||w_num_chassis||' du DSLAM '||w_nomDslam, '98');	
	END IF;
	
	RETURN w_idCarte;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkchassisexist;
--/
CREATE FUNCTION braproc_checkchassisexist (p_ligne text, p_split_ligne text[], p_eqpt_id bigint)  RETURNS bigint
  VOLATILE
AS $dbvis$
DECLARE 
	w_nomDslam VARCHAR;
	w_num_chassis NUMERIC;
	w_idChassis BIGINT;
		
BEGIN
	
	w_nomDslam := p_split_ligne[2];
	w_num_chassis := p_split_ligne[3]::NUMERIC;
	
	SELECT shlf_id FROM t_shelfs s INTO w_idChassis WHERE s.shlf_logic_shelf_num = w_num_chassis AND s.eqpt_id = p_eqpt_id;
	IF NOT FOUND THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'WN', 'Châssis inexistant sur le DSLAM '||w_nomDslam, '98');	
	END IF;
	
	RETURN w_idChassis;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkchassisnum;
--/
CREATE FUNCTION braproc_checkchassisnum (p_ligne text, p_split_ligne text[])  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_num_chassis VARCHAR;
BEGIN
	w_num_chassis := p_split_ligne[3];
	IF (braProc_isnumeric(w_num_chassis) =  false) THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Format du châssis incorrect', '4');
		isOK := FALSE;
	END IF;
	RETURN isOK;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkdslamexist;
--/
CREATE FUNCTION braproc_checkdslamexist (p_ligne text, p_split_ligne text[])  RETURNS bigint
  VOLATILE
AS $dbvis$
DECLARE 
	w_nomDslam VARCHAR;
	w_idDslam BIGINT;
		
BEGIN
	
	w_nomDslam := p_split_ligne[2];
	
	SELECT eqpt_id FROM t_equipments INTO w_idDslam WHERE eqpt_name = w_nomDslam;
	IF NOT FOUND THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'WN', 'DSLAM inexistant', '98');	
	END IF;
	
	RETURN w_idDslam;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkdslamname;
--/
CREATE FUNCTION braproc_checkdslamname (p_ligne text, p_split_ligne text[])  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_nomDslam VARCHAR;
		
BEGIN
	
	w_nomDslam := p_split_ligne[2];
	
	IF(char_length(TRIM(from w_nomDslam)) != 8)  THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Format du DSLAM incorrect', '3');	
		isOK:=false;
	END IF;
	
	RETURN isOK;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkformatetatproduction;
--/
CREATE FUNCTION braproc_checkformatetatproduction (p_ligne text, p_split_ligne text[])  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_etatProduction VARCHAR;
		
BEGIN
	
	w_etatProduction := p_split_ligne[6];
	
	IF(w_etatProduction IS DISTINCT FROM  'O' AND w_etatProduction IS DISTINCT FROM  'R' AND w_etatProduction IS DISTINCT FROM  'I' AND w_etatProduction IS DISTINCT FROM  'E')  THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Format du nouvel état de production incorrect, valeurs autorisées O(ouvert), R (réservé), I (interdit), E (eteint)', '7');	
		isOK:=false;
	END IF;
	
	RETURN isOK;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkformatsupprimercommentaire;
--/
CREATE FUNCTION braproc_checkformatsupprimercommentaire (p_ligne text, p_split_ligne text[])  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_supprimerCommentaire VARCHAR;
		
BEGIN
	
	w_supprimerCommentaire := p_split_ligne[7];
	
	IF(w_supprimerCommentaire IS DISTINCT FROM  'O' AND w_supprimerCommentaire IS DISTINCT FROM  'N')  THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Format du champ suppr_comment incorrect, valeurs autorisées O (oui), N (non)', '8');	
		isOK:=false;
	END IF;
	
	RETURN isOK;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkformattypeobjet;
--/
CREATE FUNCTION braproc_checkformattypeobjet (p_ligne text, p_split_ligne text[])  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_typeObjet VARCHAR;
		
BEGIN
	
	w_typeObjet := p_split_ligne[1];
	
	IF(w_typeObjet IS DISTINCT FROM  'D' AND w_typeObjet IS DISTINCT FROM  'S' AND w_typeObjet IS DISTINCT FROM  'C' AND w_typeObjet IS DISTINCT FROM  'P')  THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Format du type d''objet incorrect, valeurs autorisées D (Dslam), S (Châssis), C (Carte), P (Port)', '2');	
		isOK:=false;
	END IF;
	
	RETURN isOK;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checklineformat;
--/
CREATE FUNCTION braproc_checklineformat (p_ligne text, p_split_ligne text[])  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_ligne_lenght			INTEGER;
		
BEGIN
  	w_ligne_lenght = array_length(p_split_ligne, 1);
		
	-- validation de la ligne
		
	IF(w_ligne_lenght != 8)  THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Format de la ligne incorrect', '1');	
		isOK:=false;
	END IF;
	
	RETURN isOK;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkportexist;
--/
CREATE FUNCTION braproc_checkportexist (p_ligne text, p_split_ligne text[], p_carte_id bigint)  RETURNS bigint
  VOLATILE
AS $dbvis$
DECLARE 
	w_nomDslam VARCHAR;
	w_num_chassis NUMERIC;
	w_num_carte NUMERIC;
	w_num_port NUMERIC;
	w_idPort BIGINT;
		
BEGIN
	
	w_nomDslam := p_split_ligne[2];
	w_num_chassis := p_split_ligne[3]::NUMERIC;
	w_num_carte := p_split_ligne[4]::NUMERIC;
	w_num_port := p_split_ligne[5]::NUMERIC;
	
	SELECT port_id FROM t_ports INTO w_idPort WHERE port_num  = w_num_port AND card_id = p_carte_id;
	IF NOT FOUND THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'WN', 'Port inexistant sur la carte '||w_num_carte||' du chassis '||w_num_chassis||' du DSLAM '||w_nomDslam, '98');	
	END IF;
	
	RETURN w_idPort;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkportnum;
--/
CREATE FUNCTION braproc_checkportnum (p_ligne text, p_split_ligne text[])  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_num_port VARCHAR;
BEGIN
	w_num_port := p_split_ligne[5];
	IF (braProc_isnumeric(w_num_port) = false) THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Format du port incorrect', '6');	
		isOK := FALSE;
	END IF;
	RETURN isOK;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_checkremarklength;
--/
CREATE FUNCTION braproc_checkremarklength (p_ligne text, p_id_objet bigint, p_split_ligne text[], p_remark_length integer)  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	isOK BOOLEAN:=true;
	w_remark			VARCHAR;
	w_typeObjet VARCHAR;
	w_port_group_id BIGINT;
	w_supprimerCommentaire CHAR(1);
	w_new_comment VARCHAR;
		
BEGIN
	w_typeObjet := p_split_ligne[1];
	w_supprimerCommentaire := p_split_ligne[7];
	w_new_comment := p_split_ligne[8];
	
	IF(w_typeObjet = 'D') THEN
		SELECT CASE WHEN 'O' = w_supprimerCommentaire THEN w_new_comment ELSE CONCAT(eqpt_remarks, ' ', w_new_comment) END FROM t_equipments INTO w_remark WHERE eqpt_id= p_id_objet;
	ELSIF(w_typeObjet = 'S') THEN
		SELECT CASE WHEN 'O' = w_supprimerCommentaire THEN w_new_comment ELSE CONCAT(shlf_remarks, ' ', w_new_comment) END FROM t_shelfs INTO w_remark WHERE shlf_id= p_id_objet;
	ELSIF(w_typeObjet = 'C') THEN
		SELECT CASE WHEN 'O' = w_supprimerCommentaire THEN w_new_comment ELSE CONCAT(card_remarks, ' ', w_new_comment) END FROM t_cards INTO w_remark WHERE card_id= p_id_objet;	
	ELSIF(w_typeObjet = 'P') THEN
		SELECT CASE WHEN 'O' = w_supprimerCommentaire THEN w_new_comment ELSE CONCAT(port_remarks, ' ', w_new_comment) END FROM t_ports INTO w_remark WHERE port_id= p_id_objet;
		SELECT pogr_id FROM t_ports INTO w_port_group_id WHERE port_id=p_id_objet;
	END IF;
	
	IF(char_length(w_remark) > p_remark_length)  THEN
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Le champ commentaire dépasse la longueur autorisée ('||p_remark_length||')', '13');	
		isOK:=false;
	END IF;
	
	IF (isOK AND w_port_group_id IS NOT NULL) THEN
		FOR w_remark IN SELECT CASE WHEN 'O' = w_supprimerCommentaire THEN w_new_comment ELSE CONCAT(port_remarks, ' ', w_new_comment) END FROM t_ports WHERE  pogr_id = w_port_group_id AND port_id != p_id_objet
  		LOOP
  			IF(char_length(w_remark) > p_remark_length)  THEN
				INSERT INTO changeEtatProdLogTableErr(ligne,state,errMsg,errCode) VALUES(p_ligne, 'KO', 'Le champ commentaire dépasse la longueur autorisée ('||p_remark_length||')', '13');	
				isOK:=false;
				EXIT;
			END IF;
  		END LOOP;
	END IF;
	
	RETURN isOK;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_corrigerincoherenceports;
--/
CREATE FUNCTION braproc_corrigerincoherenceports ()  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 
		w_count_lignes			INTEGER;
		w_cas 					VARCHAR(20);
		w_card_id 				INTEGER;
		w_cmod_port_size		INTEGER;
		w_manf_name				VARCHAR(20);
		w_count_port_num		INTEGER;
		w_ligne  				RECORD;
		w_last_case				INTEGER;
		w_first_case			INTEGER;
		w_add_case				INTEGER;
		w_supp_case				INTEGER;
		w_port_a_traiter		INTEGER;
		w_slot_id 				INTEGER;
		w_occup					INTEGER;
		w_dslam_name			VARCHAR(20);
		w_chassis_num			INTEGER;
		w_card_num				INTEGER;
		w_card_nature			VARCHAR(1);

BEGIN	 
	
	insert into corrigerIncoherencePortsInputTable
	(select 
	b.cmod_port_size,
	a.card_id,
	d.manf_name,
	count(distinct a.port_num),
	CASE
	    WHEN (count(distinct a.port_num) - b.cmod_port_size) = 1 and d.manf_name = 'HUAWEI' 
		and exists (select port_num from t_ports where port_num=b.cmod_port_size and card_id = a.card_id)
	    THEN 'SUPP_LAST'
	    WHEN (count(distinct a.port_num) - b.cmod_port_size) = -1 and d.manf_name = 'HUAWEI' 
		and not exists (select port_num from t_ports where port_num=b.cmod_port_size-1 and card_id = a.card_id)
	    THEN 'ADD_LAST'
	    WHEN (count(distinct a.port_num) - b.cmod_port_size) = -1 and d.manf_name = 'HUAWEI' 
		and not exists (select port_num from t_ports where port_num=0 and card_id = a.card_id)
	    THEN 'ADD_FIRST'
	    WHEN (count(distinct a.port_num) - b.cmod_port_size) = 1 and d.manf_name != 'HUAWEI' 
		and exists (select port_num from t_ports where port_num=0 and card_id = a.card_id)
	    THEN 'SUPP_FIRST'
	    WHEN (count(distinct a.port_num) - b.cmod_port_size) = 1 and d.manf_name != 'HUAWEI' 
		and exists (select port_num from t_ports where port_num=b.cmod_port_size+1 and card_id = a.card_id)
	    THEN 'SUPP_LAST'
	    WHEN (count(distinct a.port_num) - b.cmod_port_size) = -1 and d.manf_name != 'HUAWEI' 
		and not exists (select port_num from t_ports where port_num=b.cmod_port_size and card_id = a.card_id)
	    THEN 'ADD_LAST'
	    ELSE 'OTHER'
	END AS CAS 
	from 
		t_ports a,
		t_card_models b,
		t_cards c,
		t_manufacturers d
		 
	where 
		a.card_id=c.card_id and c.cmod_id=b.cmod_id and b.manf_id = d.manf_id
	group by b.cmod_port_size, a.card_id, d.manf_name 
	--having count(distinct a.port_num) = b.cmod_port_size-1 or count(distinct a.port_num) = b.cmod_port_size+1);
	having count(distinct a.port_num) != b.cmod_port_size);
	
	w_count_lignes	= 0;
	SELECT	count(*) INTO w_count_lignes FROM corrigerIncoherencePortsInputTable;

	IF (w_count_lignes = 0) THEN
		INSERT INTO corrigerIncoherencePortsLogTableErr
		VALUES(null,null,null,null,null, 'WN', 'Aucun cas incohérent remonté', '98');				 
	END IF;

	--
	-- parcourir les lignes de la table
	--
  	FOR w_ligne IN SELECT cmod_port_size, card_id, manf_name, count_port_num, cas FROM corrigerIncoherencePortsInputTable 
  	LOOP
		BEGIN
		--
		-- initialisation des informations de la carte et le cas à traiter
		--

		w_card_id			:= w_ligne.card_id;
		w_cas				:= w_ligne.cas;
		w_cmod_port_size	:= w_ligne.cmod_port_size;
		w_manf_name			:= w_ligne.manf_name;
		w_count_port_num	:= w_ligne.count_port_num;
		
		--
		-- validation de la ligne
		--
		
		IF(w_cas = 'OTHER')  THEN
			INSERT INTO corrigerIncoherencePortsLogTableErr VALUES(w_cmod_port_size,w_card_id,w_manf_name,w_count_port_num,w_cas, 'WN', 'Cas incohérence de ports non prévu', '98');				 
			CONTINUE;
		END IF;
	
		--
		--selon le cas créer ou supprimer des ports
		--		
		SELECT INTO w_last_case strpos(w_cas, 'LAST');
		SELECT INTO w_first_case strpos(w_cas, 'FIRST');
		SELECT INTO w_add_case strpos(w_cas, 'ADD');
		SELECT INTO w_supp_case strpos(w_cas, 'SUPP');
		IF (w_last_case != 0 AND w_supp_case != 0) THEN
			SELECT INTO w_port_a_traiter max(port_num) FROM t_ports WHERE card_id = w_card_id;
		ELSIF (w_last_case != 0 AND w_add_case != 0) THEN
			SELECT INTO w_port_a_traiter max(port_num)+1 FROM t_ports WHERE card_id = w_card_id;
		ELSIF (w_first_case != 0 AND w_supp_case != 0) THEN
			SELECT INTO w_port_a_traiter min(port_num) FROM t_ports WHERE card_id = w_card_id;
		ELSIF (w_first_case != 0 AND w_add_case != 0) THEN
			SELECT INTO w_port_a_traiter min(port_num)-1 FROM t_ports WHERE card_id = w_card_id;
		END IF;
		
		SELECT slot_id, card_nature INTO w_slot_id, w_card_nature FROM t_cards WHERE card_id = w_card_id;
		
		IF (w_add_case != 0) THEN
		
			--ajout de port
			INSERT INTO t_ports(port_num, port_type, port_occup_status, port_occup_ont, port_occupation_status, port_activation_status, card_id, slot_id)
		    VALUES (w_port_a_traiter, w_card_nature, 0, 0, 0, 0, w_card_id, w_slot_id);
		    
		    UPDATE t_ports SET port_attribuable = 1 WHERE port_num = w_port_a_traiter AND card_id = w_card_id AND slot_id = w_slot_id;

		ELSIF (w_supp_case != 0) THEN
			--Suppression de port
			--Vérifier que le port n'est pas occupé
			SELECT INTO w_occup COALESCE(port_occup_status,0)+COALESCE(port_occup_ont,0)+COALESCE(port_occupation_status,0) FROM t_ports WHERE card_id = w_card_id AND port_num = w_port_a_traiter AND slot_id = w_slot_id;
			
			IF (w_occup > 0) THEN 
				
				SELECT INTO w_dslam_name eqpt_name FROM t_equipments WHERE eqpt_id = (SELECT eqpt_id FROM t_shelfs WHERE shlf_id = (SELECT shlf_id FROM t_slots WHERE slot_id = (SELECT slot_id FROM t_cards WHERE card_id = w_card_id)));
				SELECT INTO w_chassis_num shlf_logic_shelf_num FROM t_shelfs WHERE shlf_id = (SELECT shlf_id FROM t_slots WHERE slot_id = (SELECT slot_id FROM t_cards WHERE card_id = w_card_id));
				SELECT INTO w_card_num card_num FROM t_cards WHERE card_id = w_card_id;
				
				INSERT INTO corrigerIncoherencePortsLogTableErr VALUES(w_cmod_port_size,w_card_id,w_manf_name,w_count_port_num,w_cas, 'WN',
					CONCAT(w_dslam_name,'/',w_chassis_num,'/',w_card_num,'/',w_port_a_traiter,' : suppression port impossible car il est occupé'), '98');
				CONTINUE;
			END IF;
			--Supprimer le port, s'il est cablé il faut d'abord supprimer la colone stripe id
			DELETE FROM t_ports WHERE card_id = w_card_id AND port_num = w_port_a_traiter AND slot_id = w_slot_id;
		END IF;
		
		INSERT INTO corrigerIncoherencePortsLogTableErr VALUES(w_cmod_port_size,w_card_id,w_manf_name,w_count_port_num,w_cas, 'OK', 'Correction effectuée', '99'); 		
 	
		--
		--Fin process de la ligne
		--
		
		EXCEPTION
			WHEN OTHERS THEN
				INSERT INTO corrigerIncoherencePortsLogTableErr VALUES(w_cmod_port_size,w_card_id,w_manf_name,w_count_port_num,w_cas,'KO', SQLERRM, SQLSTATE);
				CONTINUE;
		END;
		
	-- fin FOR
	END LOOP; 
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_downgrademapping;
--/
CREATE FUNCTION braproc_downgrademapping ()  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE
	w_temp_new_mapping_release		character(12);
	w_temp_data_base_release        character(12);
BEGIN 
	SELECT apcf_release 
	INTO w_temp_new_mapping_release 
	FROM applicationConfigsTempTable
	WHERE apcf_component_name = 'Mapping';
	
	SELECT apcf_release
    INTO w_temp_data_base_release
    FROM applicationConfigsTempTable
    WHERE apcf_component_name = 'Base de donnees';
	
	UPDATE t_application_configs 
	SET apcf_release = w_temp_new_mapping_release
	WHERE apcf_component_name = 'Mapping';
	
	UPDATE t_application_configs
    SET apcf_release = w_temp_data_base_release
    WHERE apcf_component_name = 'Base de donnees';
        
	RETURN 0;											
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_insertmrtaccessmsanusage_batch;
--/
CREATE FUNCTION braproc_insertmrtaccessmsanusage_batch (num_lot integer, batch_size integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
    v_errmsg text;
    v_errcode text;
BEGIN
    BEGIN
        INSERT INTO t_mrt_access_msan_usage (
            mrdv_id,
            mrmu_hasInternet,
            mrmu_hasTV,
            mrmu_hasTOIP,
            mrmu_last_modification_time,
            mrmu_version
        )
        SELECT
            subtmadv.mrdv_id,
            CASE WHEN subtmadv.mrdv_intsiamg3offer LIKE '%NETWOO%' THEN true ELSE false END,
            CASE WHEN subtmadv.mrdv_intsiamg3offer LIKE '%MLT%' THEN true ELSE false END,
            CASE WHEN subtmadv.mrdv_intsiamg3offer LIKE '%TOIP%' THEN true ELSE false END,
            NOW(),
            0
        FROM (
	            SELECT tmadv.mrdv_id, tmadv.mrdv_intsiamg3offer
	            FROM t_mrt_access_dslam_vers tmadv
	            INNER JOIN t_mrt_access_dslams tmad ON tmad.mrtd_id = tmadv.mrtd_id
	            INNER JOIN t_technology_types ttt on tmad.tcty_id = ttt.tcty_id
	            LEFT JOIN t_mrt_access_msan_usage tmu ON tmu.mrdv_id = tmadv.mrdv_id
	            WHERE ttt.tcty_name LIKE '%FTTH%'
	            AND tmu.mrdv_id IS NULL
            LIMIT batch_size
        ) subtmadv;
    EXCEPTION
        WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS v_errmsg = MESSAGE_TEXT, v_errcode = RETURNED_SQLSTATE;
            INSERT INTO insertMrtAccessMsanUsageLogTableErr VALUES(
                num_lot,
                v_errmsg,
                v_errcode
            );
    END;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_isnumeric;
--/
CREATE FUNCTION braproc_isnumeric (text character varying)  RETURNS boolean
  VOLATILE
AS $dbvis$
DECLARE 
	x NUMERIC;
BEGIN
    x = $1::NUMERIC;
    RETURN TRUE;
EXCEPTION WHEN others THEN
    RETURN FALSE;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_miseajourobjet;
--/
CREATE FUNCTION braproc_miseajourobjet (p_ligne text, p_id_objet bigint, p_split_ligne text[])  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 
	w_new_etatProduction CHAR(1);
	w_new_etatProduction_convertie CHAR(1);
	w_old_etatProduction CHAR(1);
	w_typeObjet CHAR(1);
	w_supprimerCommentaire CHAR(1);
	w_new_comment VARCHAR;
	requeteMiseAjour VARCHAR;
	prefix_requeteMiseAjourPort VARCHAR;
	w_port_group_id BIGINT;
	w_port_id BIGINT;
		
BEGIN
	w_typeObjet := p_split_ligne[1];
	w_new_etatProduction := p_split_ligne[6];
	w_supprimerCommentaire := p_split_ligne[7];
	Select REPLACE(p_split_ligne[8],'''', '''''') into w_new_comment;
	
	-- Conversion de l'état de production
	IF(w_new_etatProduction = 'O') THEN
		w_new_etatProduction_convertie := 'O';
	ELSIF(w_new_etatProduction = 'R') THEN
		w_new_etatProduction_convertie := 'M';
	ELSIF(w_new_etatProduction = 'I') THEN
		w_new_etatProduction_convertie := 'F';
	ELSIF(w_new_etatProduction = 'E') THEN
		w_new_etatProduction_convertie := 'E';
	END IF;
	
	-- Vérification que l'état de production a été changé
	IF(w_typeObjet = 'D') THEN
		SELECT eqpt_prod_status FROM t_equipments INTO w_old_etatProduction WHERE eqpt_id= p_id_objet;
		requeteMiseAjour := 'UPDATE t_equipments SET eqpt_prod_status = '''||w_new_etatProduction_convertie||''', eqpt_remarks = CASE WHEN ''O'' = '''||w_supprimerCommentaire|| ''' THEN '''||w_new_comment||''' ELSE CONCAT(eqpt_remarks, '' '', '''||w_new_comment||''') END WHERE eqpt_id='||p_id_objet;
	ELSIF(w_typeObjet = 'S') THEN
		SELECT shlf_prod_status FROM t_shelfs INTO w_old_etatProduction WHERE shlf_id= p_id_objet;
		requeteMiseAjour := 'UPDATE t_shelfs SET shlf_prod_status = '''||w_new_etatProduction_convertie||''', 
								shlf_remarks = CASE WHEN ''O'' = '''||w_supprimerCommentaire|| ''' THEN '''||w_new_comment||''' ELSE CONCAT(shlf_remarks, '' '', '''||w_new_comment||''') END WHERE shlf_id='||p_id_objet;
	ELSIF(w_typeObjet = 'C') THEN
		SELECT card_prod_status FROM t_cards INTO w_old_etatProduction WHERE card_id= p_id_objet;
		requeteMiseAjour := 'UPDATE t_cards SET card_prod_status = '''||w_new_etatProduction_convertie||''', 
								card_remarks = CASE WHEN ''O'' = '''||w_supprimerCommentaire|| ''' THEN '''||w_new_comment||''' ELSE CONCAT(card_remarks, '' '', '''||w_new_comment||''') END WHERE card_id='||p_id_objet;
	ELSIF(w_typeObjet = 'P') THEN
		SELECT port_prod_status FROM t_ports INTO w_old_etatProduction WHERE port_id= p_id_objet;
		prefix_requeteMiseAjourPort := 'UPDATE t_ports SET port_prod_status = '''||w_new_etatProduction_convertie||''', 
								port_remarks = CASE WHEN ''O'' = '''||w_supprimerCommentaire|| ''' THEN '''||w_new_comment||''' ELSE CONCAT(port_remarks, '' '', '''||w_new_comment||''') END WHERE port_id=';
		requeteMiseAjour := prefix_requeteMiseAjourPort || p_id_objet;
	END IF;
	
	IF (w_old_etatProduction IS NOT DISTINCT FROM w_new_etatProduction_convertie) THEN
		INSERT INTO changeEtatProdLogTableErr(ligne, state, warningMsg,errCode) VALUES(p_ligne, 'WN', 'warning « Etat de production inchangé, pas de mise à jour effectuée »', '98');
	ELSE
		EXECUTE requeteMiseAjour;
		IF(w_typeObjet = 'P') THEN
			SELECT pogr_id FROM t_ports INTO w_port_group_id WHERE port_id=p_id_objet;
			-- Si le port appartient à un groupe de port, on met à jours les autres ports du groupe aussi
			IF (w_port_group_id IS NOT NULL) THEN
			
				FOR w_port_id IN SELECT port_id FROM t_ports WHERE  pogr_id = w_port_group_id AND port_id != p_id_objet
	  			LOOP
	  				requeteMiseAjour := prefix_requeteMiseAjourPort || w_port_id;
	  				EXECUTE requeteMiseAjour;
	  			END LOOP;
  			END IF;
			
		END IF;
		INSERT INTO changeEtatProdLogTableErr(ligne,state,errCode) VALUES(p_ligne, 'OK','99');
	END IF;
													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_nd_migrservtech;
--/
CREATE FUNCTION braproc_nd_migrservtech (p_repairmode integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nd		VARCHAR(15);
	w_mrtad_id 		BIGINT;
	w_mrtadv_id 		BIGINT;
	w_mrtadv_etat 		VARCHAR;
	w_oldOffreIntSiam	VARCHAR(50);
	w_newOffreIntSiam	VARCHAR(50);
	w_oldProfilLigne_id	BIGINT;
	w_oldProfilLigne	VARCHAR(50);
	w_newProfilLigne_id	BIGINT;
	w_newProfilLigne	VARCHAR(50);
	w_verifTSF		INTEGER;
	w_mrtAS_id		BIGINT;
	w_category		VARCHAR;
	w_nbRes			INTEGER;
	w_SQL_error_num		INTEGER;
	w_ISAM_error_num	INTEGER;
	w_SQL_error_info	VARCHAR(200);
        rec_in RECORD;
	rec_2 RECORD;
	rec_3 RECORD;
	rec_4 RECORD;
        cur_in CURSOR FOR SELECT nd FROM tmp_migServTech_input;
        cur2 CURSOR FOR SELECT mrtd_id FROM t_mrt_access_dslams
                        WHERE t_mrt_access_dslams.mrtd_nd = rec_in.nd;
        cur3 CURSOR FOR SELECT mrdv_id,mrdv_current_state,mrdv_intsiamg3offer,lnpr_id
                        FROM    t_mrt_access_dslam_vers t_adv
                        WHERE t_adv.mrtd_id = w_mrtad_id;

        cur4 CURSOR FOR SELECT DISTINCT mrtas_id,newTSF_id FROM tmp_migServTech_epc
                        WHERE tmp_migServTech_epc.nd = rec_in.nd;

	--***** Traitement du fichier des ND *****
	BEGIN
		-- Ouverture du 'cursor' sur les NDs.
		OPEN cur_in;
		LOOP
		-- Enregistrement de la ligne courante dans rec_in.
		FETCH cur_in INTO rec_in;
		-- EXIT de la boucle si on ne trouve plus de ligne à traiter.
		EXIT WHEN NOT FOUND;
		-- Nettoyage de la table tmp_migServTech_epc.
		DELETE FROM tmp_migServTech_epc;

		-- Initialisation des variables.
		w_nd := rec_in.nd;
		w_mrtad_id := NULL;
		w_mrtadv_id := NULL;
		w_oldOffreIntSiam := NULL;
		w_newOffreIntSiam := NULL;
		w_oldProfilLigne_id := NULL;
		w_oldProfilLigne := NULL;
		w_newProfilLigne := NULL;
		w_nbRes := 0;
		-- Ouverture du 'cursor' sur les 'mrtd_id' liés au ND courant.
		OPEN cur2;
		LOOP
		FETCH cur2 INTO rec_2;
		EXIT WHEN NOT FOUND;

		w_mrtad_id := rec_2.mrtd_id;
		w_nbRes := w_nbRes + 1;

		END LOOP;
		CLOSE cur2;

		-- Cas où on ne trouve aucun 'mrtd_id' lié au ND courant.
		IF	w_nbRes = 0
		THEN 
                        w_SQL_error_num :='-746';
                        w_ISAM_error_num :='0';
                        w_SQL_error_info := 'ND non trouve';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;

		ELSIF	w_nbRes > 1
		THEN
                        w_SQL_error_num :='-746';
                        w_ISAM_error_num :='0';
                        w_SQL_error_info := 'Plusieurs MRTAccessDSLAM associes au ND';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;

		-- Recherche MRTAccessDSLAMVers
		w_nbRes := 0;
		OPEN cur3;
                LOOP
                FETCH cur3 INTO rec_3;
                EXIT WHEN NOT FOUND;
			w_mrtadv_id := rec_3.mrdv_id;
			w_mrtadv_etat := rec_3.mrdv_current_state;
			w_oldOffreIntSiam := rec_3.mrdv_intsiamg3offer;
			w_oldProfilLigne_id := rec_3.lnpr_id;
			w_nbRes := w_nbRes + 1;
		END LOOP;
		CLOSE cur3;

		-- Verification nombre de versions trouvees
		IF	w_nbRes <> 1 
		THEN	
			w_SQL_error_num :='-746';
			w_ISAM_error_num :='0';
			w_SQL_error_info := 'Nb de MRTAccessDSLAMVers <> 1';
			INSERT INTO tmp_migServTech_epc_sav
			SELECT * FROM tmp_migServTech_epc;

			INSERT INTO tmp_migServTech_log
			VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam, 
			w_oldProfilLigne_id, w_oldProfilLigne,
			w_newOffreIntSiam, w_newProfilLigne,
			ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;
		-- Verification etat de la version du mrtacessdslam
		IF	w_mrtadv_etat <> 'C'
			THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Etat de la version du MRTAccessDSLAM incorrect : ' ||w_mrtadv_etat;
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;

		-- Verification profil ligne/libelleIntSiam
		IF    (SELECT	COUNT(*) FROM tmp_migServTech_param WHERE oldLineProfile_id = w_oldProfilLigne_id AND oldOffreIntSiamG3 = w_oldOffreIntSiam ) = 0
		THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'LibelleIntSiam et/ou profil ligne inattendu';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;

		-- Recherche des EPC/EPCVers
		INSERT INTO tmp_migServTech_epc (nd, idEPC, epcv_id, oldServTech_id, oldCategory)
		SELECT DISTINCT rec_in.nd,t_epc_vers.epc_id,t_epc_vers.epcv_id,param.oldTechService_id,param.oldTST_category
		FROM t_epc_vers,tmp_migservtech_param AS param
		WHERE  t_epc_vers.mrtd_id=w_mrtad_id
		AND param.oldOffreIntSiamG3 = w_oldOffreIntSiam
		AND param.oldLineProfile_id = w_oldProfilLigne_id 
		AND param.oldTechService_id = t_epc_vers.tcsv_id;
		-- Si aucun EPC trouve
		IF (SELECT COUNT(idEPC) FROM tmp_migServTech_epc) = 0
		THEN
			w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Aucun EPC/EPCVers trouve';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		ELSE 
			UPDATE tmp_migServTech_epc 
			SET epc_epc_id = q.epc_epc_id
			FROM (SELECT t_epcs.epc_epc_id FROM t_epcs,tmp_migServTech_epc WHERE t_epcs.epc_id = tmp_migServTech_epc.idEPC) q;
		END IF;
        
		-- controle nombre de versions
		IF (SELECT COUNT(DISTINCT tmpEPC1.epcv_id) FROM tmp_migServTech_epc AS tmpEPC1, t_epc_vers WHERE  t_epc_vers.epcv_id = tmpEPC1.epcv_id) = 0
			THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'EPC avec plusieurs versions';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;

		-- Calcul categorie
		IF (SELECT COUNT(DISTINCT oldcategory) FROM tmp_migServTech_epc) <> 1
			THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Plusieurs categories de TST initial trouvees';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		ELSE
			w_category := (SELECT DISTINCT oldcategory FROM tmp_migServTech_epc);
		END IF;

		-- si nd "Grand Public" : un seul EPC a traiter
		IF  w_category = 'G'
		THEN
			IF (SELECT COUNT(*) FROM  tmp_migServTech_epc) > 1
			THEN 
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Nb EPC/EPCVers a traiter > 1';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
			END IF;
		END IF;
        
		-- si nd "Entreprise" : un seul EPC principal
		IF w_category = 'E'
		THEN
			IF (SELECT COUNT(*) FROM tmp_migServTech_epc AS tmpEPC2
				WHERE NOT EXISTS (SELECT epc_id FROM t_epcs 
					WHERE t_epcs.epc_id = tmpEPC2.idEPC)
			) > 1
			THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Plusieurs EPC principaux';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
			END IF;
		END IF;
		
		-- Recherche des ConstitutionEPCVers
		UPDATE  tmp_migServTech_epc
		SET	const_epvc_id = q.epvc_id, 
			const_epcv_count = q.epcv_count,
			oldComposanteST_id = q.old_tsc_id, 
			mrsv_id = q.mrsv_id 
		FROM    (SELECT  MIN(t_evc.epvc_id) AS epvc_id, COUNT(*) AS epcv_count, MIN(t_evc.mrsv_id) AS mrsv_id,
					MIN(param.oldTSComponent_id) AS old_tsc_id
				FROM    tmp_migServTech_param AS param, t_epc_vers_comps AS t_evc, tmp_migServTech_epc AS tme
				WHERE   param.oldOffreIntSiamG3 = w_oldOffreIntSiam
				AND   param.oldLineProfile_id = w_oldProfilLigne_id
				AND   param.oldTechService_id = tme.oldServTech_id
				AND   param.oldTSComponent_id = t_evc.stco_id
				AND   tme.epcv_id = t_evc.epcv_id
			) q ;

		IF EXISTS (SELECT nd FROM tmp_migServTech_epc WHERE const_epcv_count <> 1)
			THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Nb de ConstitutionEPCVers <> 1';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;

		-- recherche des MRTAccessServiceVers
		UPDATE	tmp_migServTech_epc
		SET	mrtas_id = q.mras_id,
			oldProfilATM_id = q.atpr_id
		FROM	(SELECT t_masv.mras_id AS mras_id, t_masv.atpr_id::INT AS atpr_id
				FROM    t_mrt_access_service_vers t_masv, tmp_migServTech_epc AS t
				WHERE   t_masv.mrsv_id = t.mrsv_id
		) q ;

		-- controle MRTAccessService/MRTAccessServiceVers trouve
		IF EXISTS (SELECT nd FROM tmp_migServTech_epc WHERE mrtas_id IS NULL)
                        THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Nb de MRTAccessServiceVers <> 1';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;

		-- controle nombre de versions de la MRTAccessService
		IF EXISTS (SELECT  nd FROM tmp_migServTech_epc AS tmpEPC, t_mrt_access_service_vers AS t_masv
				WHERE   t_masv.mras_id = tmpEPC.mrtas_id
				AND   t_masv.mrsv_vers_num::INT > 1)

		THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'MRTAccessService avec plusieurs versions';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;

		-- Controle du parametrage initial du ND
		UPDATE	tmp_migServTech_epc
		SET	oldProfilLigne = q.oldLineProfile , newProfilLigne_id = q.newLineProfile_id , 
			newProfilLigne = q.newLineProfile , newLibIntSiam = q.newOffreIntSiamG3 ,
			oldServTech    = q.oldTechService , newServTech_id = q.newTechService_id , 
			newServTech    = q.newTechService , oldComposanteST = q.oldTSComponent, 
			newComposanteST_id = q.newTSComponent_id , newComposanteST = q.newTSComponent,
			oldProfilATM   = q.oldATMProfile , newProfilATM_id = q.newATMProfile_id,
			newProfilATM   = q.newATMProfile , newTSF_id = q.newTSF_id
		FROM ( SELECT  
			param.oldLineProfile, param.newLineProfile_id,
			param.newLineProfile , param.newOffreIntSiamG3,
			param.oldTechService , param.newTechService_id, 
			param.newTechService , param.oldTSComponent,
			param.newTSComponent_id , param.newTSComponent,
			param.oldATMProfile , param.newATMProfile_id, 
			param.newATMProfile , param.newTSF_id
			FROM    tmp_migServTech_param AS param, tmp_migServTech_epc AS tm_epc
			WHERE   param.oldOffreIntSiamG3 = w_oldOffreIntSiam
				AND   param.oldLineProfile_id = w_oldProfilLigne_id
				AND   param.oldTechService_id = tm_epc.oldServTech_id
                                AND   param.oldTSComponent_id = tm_epc.oldComposanteST_id
                                AND   param.oldATMProfile_id  =  tm_epc.oldProfilATM_id
		   ) q;
                     
		-- Verification correspondance parametrage trouve
		IF EXISTS (SELECT nd FROM tmp_migServTech_epc WHERE newProfilLigne_id IS NULL)
			THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Parametrage initial du ND incorrect';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		END IF;

		-- Calcul profil ligne
		IF (SELECT COUNT(DISTINCT newProfilLigne_id) FROM tmp_migServTech_epc) <> 1
                        THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Plusieurs profil ligne cible possibles';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		ELSE
			w_oldProfilLigne := (SELECT DISTINCT oldProfilLigne FROM tmp_migServTech_epc);
			w_newProfilLigne := (SELECT DISTINCT newProfilLigne FROM tmp_migServTech_epc);
			w_newProfilLigne_id := (SELECT DISTINCT newProfilLigne_id FROM tmp_migServTech_epc);
		END IF;
		-- Calcul libelleIntSiam
		IF (SELECT COUNT(DISTINCT newLibIntSiam) FROM tmp_migServTech_epc) <> 1
                THEN
                        w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'Plusieurs LibelleIntSiam cible possibles';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
		ELSE
				w_newOffreIntSiam := (SELECT DISTINCT newLibIntSiam FROM  tmp_migServTech_epc);
		END IF;



	-- ND "Grand Public" : controle format idEPC et calcul nouvelle valeur
	IF w_category = 'G'
	THEN
		IF EXISTS (SELECT nd FROM tmp_migServTech_epc WHERE substring(epc_epc_id,11,1) <> '+')
		THEN -- Prise en compte cas FTTH avec EPC sur 9 caracteres
			IF EXISTS (SELECT nd FROM tmp_migServTech_epc WHERE substring(epc_epc_id,10,1) = '+')
			THEN
				UPDATE tmp_migServTech_epc
	        	 	SET newIdEPC = '0' || substring(epc_epc_id,1,10) || newServTech_id ;
			ELSE 
				w_SQL_error_num  := '-746';
                        	w_ISAM_error_num := '0';
                        	w_SQL_error_info := 'Format idEPC incorrect';
                       	 	INSERT INTO tmp_migServTech_epc_sav
                        	SELECT * FROM tmp_migServTech_epc;

                        	INSERT INTO tmp_migServTech_log
                        	VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                       	 	w_oldProfilLigne_id, w_oldProfilLigne,
                        	w_newOffreIntSiam, w_newProfilLigne,
                        	ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
                        	CONTINUE;

			END IF;
		ELSE
			UPDATE	tmp_migServTech_epc
			SET	newIdEPC = substring(epc_epc_id,1,11) || newServTech_id ;
		END IF;
	END IF;



		-- Verification de la presence de la nouvelle TSF sur la ressource de collecte
		OPEN cur4;
                LOOP
                FETCH cur4 INTO rec_4;
                EXIT WHEN NOT FOUND;
			w_verifTSF := rec_4.newTSF_id;
			w_mrtAS_id := rec_4.mrtas_id;
			IF NOT EXISTS ( SELECT rpro_id FROM t_res_prod_roles 
					WHERE tsft_id= w_verifTSF 
					AND rpct_id=(SELECT rpct_id FROM t_resource_usages 
					WHERE mras_id= w_mrtAS_id 
					AND	rsus_index=(SELECT max(rsus_index) FROM t_resource_usages 
					WHERE mras_id= w_mrtAS_id))
					)
			THEN
			w_SQL_error_num  := '-746';
                        w_ISAM_error_num := '0';
                        w_SQL_error_info := 'nouveau serv tech non supporte par ressource de collecte';
                        INSERT INTO tmp_migServTech_epc_sav
                        SELECT * FROM tmp_migServTech_epc;

                        INSERT INTO tmp_migServTech_log
                        VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam,
                        w_oldProfilLigne_id, w_oldProfilLigne,
                        w_newOffreIntSiam, w_newProfilLigne,
                        ABS(w_ISAM_error_num) || '/' || TRIM(w_SQL_error_info) , w_SQL_error_num);
			CONTINUE;
			END IF;
		END LOOP;
		CLOSE cur4;
		-- Execution des mises a jour
		IF	p_repairMode = 1
		THEN
			-- MRTAccessDSLAMVers -> offreIntSiam
			-- MRTAccessDSLAMVers -> profilLigne
			UPDATE	t_mrt_access_dslam_vers
			SET     mrdv_intsiamg3offer = w_newOffreIntSiam, lnpr_id = w_newProfilLigne_id
			WHERE	mrdv_id = w_mrtadv_id;
			-- EPCVers -> serviceTechnique
			UPDATE	t_epc_vers
			SET	tcsv_id = t.newServTech_id
			FROM    tmp_migServTech_epc AS t
			WHERE  	 t.epcv_id = t_epc_vers.epcv_id;
			-- ConstitutionEPCVers -> composanteST
			UPDATE	t_epc_vers_comps
			SET	stco_id = t.newComposanteST_id
			FROM    tmp_migServTech_epc AS t
			WHERE   t.const_epvc_id = t_epc_vers_comps.epvc_id;
			-- MRTAccessServiceVers -> profilATM
			UPDATE  t_mrt_access_service_vers 
			SET	atpr_id = t.newProfilATM_id
			FROM    tmp_migServTech_epc AS t
			WHERE   t.mrsv_id = t_mrt_access_service_vers.mrsv_id;
	
			-- Si ND "Grand Public" : modification idEPC
			IF w_category = 'G'
			THEN
				UPDATE  t_epcs
				SET	epc_epc_id = t.newIdEPC, epc_old_id_epc=t.epc_epc_id
				FROM    tmp_migServTech_epc AS t
				WHERE   t_epcs.epc_id = t.idEPC;
			END IF;
		END IF;

		INSERT INTO tmp_migServTech_log
		VALUES(w_nd, w_mrtad_id, w_mrtadv_id,
		w_oldOffreIntSiam, w_oldProfilLigne_id, w_oldProfilLigne,
		w_newOffreIntSiam, w_newProfilLigne, '' , 0);

		INSERT INTO tmp_migServTech_epc_sav
                SELECT * FROM tmp_migServTech_epc;

	END LOOP;
	
	CLOSE cur_in;	

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_nd_migrservtech;
--/
CREATE FUNCTION braproc_nd_migrservtech (p_repairmode smallint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nd		VARCHAR(15);
	w_mrtad_id 		BIGINT;
	w_mrtadv_id 		BIGINT;
	w_mrtadv_etat 		CHAR(1);
	w_oldOffreIntSiam	VARCHAR(50);
	w_newOffreIntSiam	VARCHAR(50);
	w_oldProfilLigne_id	BIGINT;
	w_oldProfilLigne		VARCHAR(50);
	w_newProfilLigne_id	BIGINT;
	w_newProfilLigne		CHAR(50);
	w_verifTSF		INTEGER;
	w_mrtAS_id		BIGINT;
	w_category		CHAR(1);
	w_nbRes			INTEGER;
	w_SQL_error_num		INTEGER;
	w_ISAM_error_num		INTEGER;
	w_SQL_error_info		VARCHAR(200);
	l_t_mrt_adv t_mrt_access_dslam_vers%rowtype;
        rec_in RECORD;
        cur2 CURSOR FOR SELECT mrtd_id FROM t_mrt_access_dslams
                        WHERE t_mrt_access_dslams.mrtd_nd = rec_in.nd;
        cur3 CURSOR FOR SELECT mrdv_id,mrdv_current_state,mrdv_intsiamg3offer,lnpr_id
                        FROM    t_mrt_access_dslam_vers t_adv
                        WHERE t_adv.mrtd_id = w_mrtad_id;
        l_t_mig_epc RECORD;
        cur4 CURSOR FOR SELECT DISTINCT newTSF_id, mrtas_id
                        FROM tmp_migServTech_epc AS t;
        cur_in CURSOR FOR SELECT nd FROM tmp_migServTech_input;



	--***** Traitement du fichier des ND *****
	BEGIN
		-- Open the cursor
		OPEN cur_in;
		LOOP
		-- fetch row into rec_in
		FETCH cur_in INTO rec_in;

		-- exit when no more row to fetch
		EXIT WHEN NOT FOUND;
	
		w_mrtad_id := NULL;
		w_mrtadv_id := NULL;
		w_oldOffreIntSiam := NULL;
		w_newOffreIntSiam := NULL;
		w_oldProfilLigne_id := NULL;
		w_oldProfilLigne := NULL;
		w_newProfilLigne := NULL;
		-- Recherche MRTAccessDSLAM
		w_nbRes := 0;
		OPEN cur2;
			LOOP
			FETCH cur2 INTO w_mrtad_id;
               		EXIT WHEN NOT FOUND;
			w_nbRes := w_nbRes + 1;
			END LOOP;
			CLOSE cur2;
			RAISE INFO 'FIN cur2' ;
		
		IF	w_nbRes = 0
			THEN RAISE EXCEPTION '-746','0',"ND non trouve";
		ELSIF	w_nbRes > 1
			THEN RAISE EXCEPTION '-746', '0', "Plusieurs MRTAccessDSLAM associes au ND";
		END IF;

		-- Recherche MRTAccessDSLAMVers
		w_nbRes := 0;
	
		OPEN cur3;
                LOOP
                FETCH cur3 INTO l_t_mrt_adv;
                EXIT WHEN NOT FOUND;
			w_mrtadv_id := t_adv.mrdv_id;
			w_mrtadv_etat := t_adv.mrdv_current_state;
			w_oldOffreIntSiam := t_adv.mrdv_intsiamg3offer;
			w_oldProfilLigne_id := t_adv.lnpr_id;
			w_nbRes := w_nbRes + 1;
		END LOOP;
		CLOSE cur3;
                RAISE INFO 'fin cur3';
		
		-- Verification nombre de versions trouvees
		IF	w_nbRes <> 1 THEN	
			RAISE INFO 'fin cur3';
			w_SQL_error_num :='-746';
			w_ISAM_error_num :='0';
			w_SQL_error_info := 'Nb de MRTAccessDSLAMVers <> 1';
			INSERT INTO tmp_migServTech_epc_sav
			SELECT * FROM tmp_migServTech_epc;

			INSERT INTO tmp_migServTech_log
			VALUES (w_nd, w_mrtad_id, w_mrtadv_id, w_oldOffreIntSiam, 
			w_oldProfilLigne_id, w_oldProfilLigne,
			w_newOffreIntSiam, w_newProfilLigne,
			ABS(w_ISAM_error_num)||'/'||TRIM(w_SQL_error_info) , w_SQL_error_num);
			RETURN;
		END IF;
		RAISE INFO 'fin cur3';	
		-- Verification etat de la version du mrtacessdslam
		IF	w_mrtadv_etat <> 'C'
			THEN	RAISE EXCEPTION '-746', '0', "Etat de la version du MRTAccessDSLAM incorrect : "||w_mrtadv_etat;
		END IF;
        
		-- Verification profil ligne/libelleIntSiam
		IF    (SELECT	COUNT(*) FROM tmp_migServTech_param WHERE oldLineProfile_id = w_oldProfilLigne_id AND oldOffreIntSiamG3 = w_oldOffreIntSiam ) = 0
			THEN RAISE EXCEPTION '-746', '0', "LibelleIntSiam et/ou profil ligne inattendu";
		END IF;

		-- Recherche des EPC/EPCVers
		INSERT INTO tmp_migServTech_epc (nd, epc_id, oldIdEPC, epcv_id, oldServTech_id, oldCategory)
		SELECT DISTINCT rec_in.nd, t_epcs.epc_id, t_epcs.epc_epc_id, t_epcv.epcv_id, t_epcv.tcsv_id, param.oldTST_category
		FROM	tmp_migservtech_param AS param, t_epcs, t_mrt_access_dslam_vers AS t_madv, t_epc_vers AS t_epcv
		WHERE	param.oldOffreIntSiamG3 = w_oldOffreIntSiam
			AND	param.oldLineProfile_id = w_oldProfilLigne_id
			AND t_madv.mrtd_id =  w_mrtad_id
			AND t_madv.mrdv_intsiamg3offer = w_oldOffreIntSiam
			AND t_epcv.mrtd_id =  w_mrtad_id
			AND	t_epcv.epc_id = t_epcs.epc_id
			AND	t_epcv.tcsv_id = param.oldTechService_id;

		-- Si aucun EPC trouve
		IF (SELECT COUNT(*) FROM tmp_migServTech_epc) = 0
		THEN
			RAISE EXCEPTION '-746', '0', "Aucun EPC/EPCVers trouve";
		END IF;
        
		-- controle nombre de versions
		IF (SELECT COUNT(DISTINCT epcv_id) FROM	 tmp_migServTech_epc AS tmpEPC1, t_epc_vers WHERE  t_epc_vers.epcv_id = tmpEPC1.epcv_id) = 0
			THEN RAISE EXCEPTION '-746', '0', "EPC avec plusieurs versions";
		END IF;

		-- Calcul categorie
		IF (SELECT COUNT(DISTINCT oldcategory) FROM tmp_migServTech_epc) <> 1
			THEN RAISE EXCEPTION '-746', '0', "Plusieurs categories de TST initial trouvees";
		ELSE
			w_category := (SELECT DISTINCT oldcategory FROM tmp_migServTech_epc);
		END IF;

		-- si nd "Grand Public" : un seul EPC a traiter
		IF  w_category = "G"
		THEN
			IF (SELECT COUNT(*) FROM  tmp_migServTech_epc) > 1
				THEN RAISE EXCEPTION '-746', '0', "Nb EPC/EPCVers a traiter > 1";
			END IF;
		END IF;
        
		-- si nd "Entreprise" : un seul EPC principal
		IF w_category = "E"
		THEN
			IF (SELECT COUNT(*) FROM tmp_migServTech_epc AS tmpEPC2
				WHERE NOT EXISTS (SELECT epc_id FROM t_epcs 
					WHERE t_epcs.epc_id = tmpEPC2.epc_id)
			) > 1
			THEN RAISE EXCEPTION '-746', '0', "Plusieurs EPC principaux";
			END IF;
		END IF;
	
		
		-- Recherche des ConstitutionEPCVers
		UPDATE  tmp_migServTech_epc AS t
		SET	t.const_epvc_id = q.epvc_id, 
			t.const_epcv_count = q.epcv_count,
			t.oldComposanteST_id = q.old_tsc_id, 
			t.mrsv_id = q.mrsv_id 
		FROM    (SELECT  MIN(t_evc.epvc_id) AS epvc_id, COUNT(*) AS epcv_count,
				MIN(param.oldTSComponent_id) AS old_tsc_id, t_evc.mrsv_id AS mrsv_id
				FROM      tmp_migServTech_param AS param, t_epc_vers_comps AS t_evc
				WHERE   param.oldOffreIntSiamG3 = w_oldOffreIntSiam
				AND   param.oldLineProfile_id = w_oldProfilLigne_id
				AND   param.oldTechService_id = t.oldServTech_id
				AND   t_evc.stco_id = param.oldTSComponent_id
				AND   t_evc.epcv_id = t.epcv_id
			) q ;

		IF EXISTS (SELECT nd FROM tmp_migServTech_epc WHERE const_epcv_count <> 1)
			THEN RAISE EXCEPTION '-746', '0', "Nb de ConstitutionEPCVers <> 1";
		END IF;

		-- recherche des MRTAccessServiceVers
		UPDATE	tmp_migServTech_epc AS t
		SET	t.mrtas_id = q.mras_id,
			t.oldProfilATM_id = q.atpr_id
		FROM	(SELECT t_masv.mras_id AS mras_id, t_masv.atpr_id::INT AS atpr_id
				FROM    t_mrt_access_service_vers t_masv
				WHERE   t_masv.mrsv_id = t.mrsv_id
		) q ;

		-- controle MRTAccessService/MRTAccessServiceVers trouve
		IF EXISTS (SELECT nd FROM tmp_migServTech_epc WHERE mrtas_id IS NULL)
			THEN RAISE EXCEPTION '-746', '0', "Nb de MRTAccessServiceVers <> 1";
		END IF;
        
		-- controle nombre de versions de la MRTAccessService
		IF EXISTS (SELECT  nd FROM tmp_migServTech_epc tmpEPC7, t_mrt_access_service_vers t_masv
				WHERE   t_masv.id = tmpEPC7.mrtas_id
				AND   t_masv.mras_vers_num_0::INT <> 0
				AND   t_masv.mras_vers_num_1::INT <> 0)
			THEN RAISE EXCEPTION '-746', '0', "MRTAccessService avec plusieurs versions";
		END IF;

		-- Controle du parametrage initial du ND
		UPDATE	tmp_migServTech_epc AS t
		SET	t.oldProfilLigne = q.p_opl , t.newProfilLigne_id = q.p_nlp_id , 
			t.newProfilLigne = q.p_nlp , t.newLibIntSiam = q.p_noisg , 
			t.oldServTech    = q.p_ots , t.newServTech_id = q.p_nts_id , 
			t.newServTech    = q.p_nts , t.oldComposanteST = q.p_otsc, 
			t.newComposanteST_id = q.p_ntsc_id , t.newComposanteST = q.p_ntsc,
			t.oldProfilATM   = q.p_oap , t.newProfilATM_id = q.p_nap_id, 
			t.newProfilATM   = q.p_nap , t.newTSF_id = q.p_ntsf_id
		FROM ( SELECT  
			param.oldLineProfile AS p_olp, param.newLineProfile_id AS p_nlp_id,
			param.newLineProfile AS p_nlp, param.newOffreIntSiamG3 AS p_noisg,
			param.oldTechService AS p_ots, param.newTechService_id AS nts_id, 
			param.newTechService AS p_nts, param.oldTSComponent AS p_otsc,
			param.newTSComponent_id AS p_ntsc_id, param.newTSComponent AS p_ntsc,
			param.oldATMProfile  AS p_oap, param.newATMProfile_id AS p_nap_id, 
			param.newATMProfile  AS p_nap, param.newTSF_id AS p_ntsf_id
			FROM    tmp_migServTech_param param
			WHERE   
				param.oldOffreIntSiamG3 = w_oldOffreIntSiam
				AND param.oldLineProfile_id = w_oldProfilLigne_id
				AND   param.oldTechService_id = tmp_migServTech_epc.oldServTech_id
				AND   param.oldTSComponent_id = tmp_migServTech_epc.oldComposanteST_id
				AND   param.oldATMProfile_id =  tmp_migServTech_epc.oldProfilATM_id
		   ) q;
                     
		-- Verification correspondance parametrage trouve
		IF EXISTS (SELECT nd FROM tmp_migServTech_epc WHERE newProfilLigne_id IS NULL)
			THEN RAISE EXCEPTION '-746', '0', "Parametrage initial du ND incorrect";
		END IF;

		-- Calcul profil ligne
		IF (SELECT COUNT(DISTINCT newProfilLigne_id) FROM tmp_migServTech_epc) <> 1
			THEN RAISE EXCEPTION '-746', '0', "Plusieurs profil ligne cible possibles";
		ELSE
			w_oldProfilLigne := (SELECT DISTINCT oldProfilLigne FROM tmp_migServTech_epc);
			w_newProfilLigne := (SELECT DISTINCT newProfilLigne FROM tmp_migServTech_epc);
			w_newProfilLigne_id := (SELECT DISTINCT newProfilLigne_id FROM tmp_migServTech_epc);
		END IF;

		-- Calcul libelleIntSiam
		IF (SELECT COUNT(DISTINCT newLibIntSiam) FROM tmp_migServTech_epc) <> 1
			THEN RAISE EXCEPTION '-746', '0', "Plusieurs LibelleIntSiam cible possibles";
		ELSE
			w_newOffreIntSiam := (SELECT DISTINCT newLibIntSiam FROM  tmp_migServTech_epc);
		END IF;
					
		-- Verification de la presence de la nouvelle TSF sur la ressource de collecte
		OPEN cur4;
                LOOP
                FETCH cur4 INTO l_t_mig_epc;
                EXIT WHEN NOT FOUND;
			w_verifTSF := t.newTSF_id;
			w_mrtAS_id := t.mrtas_id;
			IF NOT EXISTS ( SELECT rpro_id FROM t_res_prod_roles 
					WHERE tsft_id= w_verifTSF 
					AND rpct_id=(SELECT rpct_id FROM t_resource_usages 
					WHERE mras_id= w_mrtAS_id 
					AND	rsus_index=(SELECT max(rsus_index) FROM t_resource_usages 
					WHERE mras_id= w_mrtAS_id))
					)
			THEN RAISE EXCEPTION '-746', '0', "nouveau serv tech non supporte par ressource de collecte";
			END IF;
 		CLOSE cur4;
                RAISE INFO 'fin cur4' ;
		END LOOP;


		-- Execution des mises a jour
		IF	p_repairMode = 1
		THEN
			-- MRTAccessDSLAMVers -> offreIntSiam
			-- MRTAccessDSLAMVers -> profilLigne			
			UPDATE	t_mrt_access_dslam_vers
			SET     mrdv_intsiamg3offer = w_newOffreIntSiam, lnpr_id = w_newProfilLigne_id
			WHERE	mrdv_id = w_mrtadv_id;
								
			-- EPCVers -> serviceTechnique
			UPDATE	t_epc_vers
			SET	tcsv_id = RPAD(t.newServTech_id, 5, ' ')
			FROM    tmp_migServTech_epc AS t
			WHERE  	 t.epcv_id = t_epc_vers.epcv_id;
			
			-- ConstitutionEPCVers -> composanteST
			UPDATE	t_epc_vers_comps
			SET	stco_id = RPAD(t.newComposanteST_id, 6, ' ')
			FROM    tmp_migServTech_epc AS t
			WHERE   t.const_epvc_id = t_epc_vers_comps.epvc_id;

			-- MRTAccessServiceVers -> profilATM
			UPDATE  t_mrt_access_service_vers 
			SET	atpr_id = RPAD(t.newProfilATM_id, 3, ' ')
			FROM    tmp_migServTech_epc AS t
			WHERE   t.mrsv_id = t_mrt_access_service_vers.mrsv_id;
			
			-- Si ND "Grand Public" : modification idEPC
			IF w_category = "G"
			THEN
				UPDATE  t_epc_vers
				SET	epc_id = newIdEPC
				FROM    tmp_migServTech_epc AS t
				WHERE   t.epcv_id  = t_epc_vers.epcv_id;
			END IF;
		END IF;

	END LOOP;
	
	CLOSE cur_in;	

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_suppvcmulti;
--/
CREATE FUNCTION braproc_suppvcmulti ()  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 

		w_nd TEXT;
		w_shmd_id BIGINT;
		w_epcVersRecord RECORD;
		w_mrtADRecord RECORD;
		w_has_multiservice BOOLEAN;
		w_has_DSLAM_ISAM BOOLEAN;
		w_mras_id BIGINT;
		w_mrsv_state VARCHAR(1); 
		w_nbreMrtAD SMALLINT;
BEGIN	
	
		
	--
	-- parcourir les nd de la table
	--
	
  	FOR w_nd IN SELECT nd FROM suppVCMultiLogInputTable 
  	LOOP
			
		BEGIN	
  		w_has_multiservice := false;
  		w_has_DSLAM_ISAM := false;
  		
  		-- TODO: Controle format de la ligne: à demander 
  		--		FSC ND de type INT(9)
  		--		JIRA ND 9 ou 10 caractère
  		--      Pour ADSLE : ND alphanumerique et plus de controle de taille
  		IF (NOT w_nd ~ ('^[a-zA-Z0-9]+$')) THEN --IF (w_nd ~ ('^[0-9]{9}$')) THEN
  			INSERT INTO suppVCMultiLogTableErr VALUES(w_nd, 'KO', 'Format de la ligne incorrect', '1');
  			CONTINUE;
  		END IF;
  	
  		-- Controle d'existence du nd ( presence du nd dans la table mrt_access_dslam) 
  		--SELECT mrtd_id, a_port_id, a_pogr_id INTO w_mrtd_id, w_port_id, w_pogr_id FROM t_mrt_access_dslams WHERE mrtd_nd = w_nd;
  		SELECT COUNT(*) INTO w_nbreMrtAD FROM t_mrt_access_dslams WHERE mrtd_nd = w_nd;
		IF (w_nbreMrtAD <=0) THEN
			INSERT INTO suppVCMultiLogTableErr VALUES(w_nd, 'KO', 'ND inexistant', '3');
			CONTINUE;
		END IF; 
  	
  		FOR w_mrtADRecord IN SELECT mrtd_id, a_port_id, a_pogr_id FROM t_mrt_access_dslams WHERE mrtd_nd = w_nd
  		LOOP
			-- Controle que le nd est sur un dslam ISAM XD (mrt_access_dslam.port.shelf.shelfmodel) 
			IF(w_mrtADRecord.a_port_id IS NOT NULL) THEN
				SELECT sm.shmd_id INTO w_shmd_id FROM t_shelf_models sm NATURAL JOIN t_shelfs sh NATURAL JOIN t_slots sl NATURAL JOIN t_ports p WHERE port_id = w_mrtADRecord.a_port_id AND sm.shmd_name='ISAMXD';
			ELSE
				SELECT sm.shmd_id INTO w_shmd_id FROM t_shelf_models sm NATURAL JOIN t_shelfs sh NATURAL JOIN t_slots sl NATURAL JOIN t_ports p WHERE pogr_id = w_mrtADRecord.a_pogr_id AND sm.shmd_name='ISAMXD' LIMIT 1;
			END IF;
			
			IF (NOT FOUND) THEN
				CONTINUE;
			ELSE
				w_has_DSLAM_ISAM := true;
			END IF; 
			
			
			-- Controle que le nd posséde l'EPC multiservice
			
			FOR w_epcVersRecord IN SELECT epcv.* FROM t_epc_vers epcv NATURAL JOIN t_tech_services ts NATURAL JOIN t_tech_serv_types tst WHERE epcv.mrtd_id=w_mrtADRecord.mrtd_id AND tst.tst_name LIKE 'MULTISERVICE%' 
			LOOP
				w_has_multiservice := true;
				
				-- recherché des mrt access services de type multiservice associés à l'epcVers
				SELECT mrtAsVers.mras_id, mrtAsVers.mrsv_current_state INTO w_mras_id,w_mrsv_state FROM t_epc_vers_comps epvc NATURAL JOIN t_mrt_access_service_vers mrtAsVers WHERE  epvc.epcv_id = w_epcVersRecord.epcv_id;
				
				IF ((SELECT COUNT(*) FROM t_epc_vers WHERE epc_id = w_epcVersRecord.epc_id) = 1) THEN
				
					-- Suppression de l'EPC ==> l'EPC vers va être supprimer par trigger
					DELETE FROM t_epcs WHERE epc_id = w_epcVersRecord.epc_id;
				ELSE
					-- Suppression de l'EPC vers seulement
					DELETE FROM t_epc_vers WHERE epcv_id = w_epcVersRecord.epcv_id;
				END IF;
				
				-- Suppression des MrtAccessService
				DELETE FROM t_mrt_access_services WHERE mras_id = w_mras_id;
				
				-- MAJ mras_utilisation des mrtAccessService INTERNET et TOIP de même état
				FOR w_epcVersRecord IN SELECT epcv.* FROM t_epc_vers epcv NATURAL JOIN t_tech_services ts NATURAL JOIN t_tech_serv_types tst WHERE epcv.mrtd_id=w_mrtADRecord.mrtd_id AND (tst.tst_name LIKE 'TOIP%' OR tst.tst_is_internet = '1')
				LOOP
					
					UPDATE t_mrt_access_services SET mras_utilisation = 1 WHERE mras_utilisation = 0 AND mras_id IN (
						SELECT mrtAsVers.mras_id FROM t_epc_vers_comps epvc NATURAL JOIN t_mrt_access_service_vers mrtAsVers 
						WHERE  epvc.epcv_id = w_epcVersRecord.epcv_id AND mrtAsVers.mrsv_current_state=w_mrsv_state 
					);
					
				END LOOP; -- Fin boucle epcVers Internet et TOIP
			END LOOP; -- Fin boucle epcVers Multiservice
		END LOOP; -- Fin boucle mrtAccessDslam
  	
		IF (NOT w_has_DSLAM_ISAM) THEN
			INSERT INTO suppVCMultiLogTableErr VALUES(w_nd, 'KO', 'DSLAM non ISAM XD', '4');
			CONTINUE;
		END IF; 
		
		IF(NOT w_has_multiservice) THEN
			INSERT INTO suppVCMultiLogTableErr VALUES(w_nd, 'KO', 'Pas de VC Multiservice', '5');
			CONTINUE;
		END IF;
		
		
		INSERT INTO suppVCMultiLogTableErr VALUES(w_nd, 'OK', 'VC multiservice supprimé', '99');
		
		EXCEPTION
			WHEN OTHERS THEN
				INSERT INTO suppVCMultiLogTableErr	VALUES(w_nd, 'KO', SQLERRM, SQLSTATE);
				CONTINUE;
		END;
		
	-- fin FOR
	END LOOP;  -- Fin boucle ND
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_tstnonpresent;
--/
CREATE FUNCTION braproc_tstnonpresent (p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_newcardmodelfamille character, p_oldswversion character)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
		tstName  RECORD;		  		
BEGIN

    FOR tstName IN SELECT ttst.tst_name
		FROM  t_card_national_profiles tcnp, t_techno_on_card_nat_profiles ttocnp, t_tst_on_card_nat_profiles tcp , t_tech_serv_types ttst
		WHERE tcnp.cnpr_id = ttocnp.cnpr_id 
		AND tcp.cnpr_id = tcnp.cnpr_id
		AND ttst.tst_id = tcp.tst_id 
		AND tcnp.csfv_id = p_oldSWVersionId
		AND ttst.tst_id not in (
			SELECT tcp.tst_id
			FROM  t_card_national_profiles tcnp, t_techno_on_card_nat_profiles ttocnp, t_tst_on_card_nat_profiles tcp 
			WHERE tcnp.cnpr_id = ttocnp.cnpr_id 
			AND tcp.cnpr_id = tcnp.cnpr_id
			AND tcnp.csfv_id = p_newSWVersionId
		)
	LOOP
	
	
	INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId,p_newSWVersion, p_newSWVersionId,p_hwVersion,p_newCardModelFamille,
						'WARNING: TST ferme non present pour nouvelle ' || p_newCardModel ||'/' || p_newSWVersion || ':' || tstName,
  			0);
		
		-- fin FOR
	END LOOP;
	
	RETURN 0;
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_tstnonpresent;
--/
CREATE FUNCTION braproc_tstnonpresent (p_repairmode integer, p_eqptlog character, p_chassisno smallint, p_cardno smallint, p_cardid bigint, p_oldcardmodel character, p_oldcardmodid bigint, p_oldswversionid bigint, p_newcardmodel character, p_newcardmodid bigint, p_newswversion character, p_newswversionid bigint, p_hwversion character, p_oldhwversion character, p_oldpcpmodelnumber integer, p_newpcpmodelnumber integer, p_chassisid bigint, p_newcardmodelfamille character, p_oldswversion character)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
		tstName  RECORD;		  		
BEGIN

    FOR tstName IN SELECT ttst.tst_name
		FROM  t_card_national_profiles tcnp, t_techno_on_card_nat_profiles ttocnp, t_tst_on_card_nat_profiles tcp , t_tech_serv_types ttst
		WHERE tcnp.cnpr_id = ttocnp.cnpr_id 
		AND tcp.cnpr_id = tcnp.cnpr_id
		AND ttst.tst_id = tcp.tst_id 
		AND tcnp.csfv_id = p_oldSWVersionId
		AND ttst.tst_id not in (
			SELECT tcp.tst_id
			FROM  t_card_national_profiles tcnp, t_techno_on_card_nat_profiles ttocnp, t_tst_on_card_nat_profiles tcp 
			WHERE tcnp.cnpr_id = ttocnp.cnpr_id 
			AND tcp.cnpr_id = tcnp.cnpr_id
			AND tcnp.csfv_id = p_newSWVersionId
		)
	LOOP
	
	
	INSERT INTO changeCardModelLogTableErr
		VALUES(p_eqptLog, p_chassisNo,p_chassisId, p_cardNo, p_cardId,
					p_oldCardModel,p_oldCardModId, p_oldSWVersion,p_oldSWVersionId,
					p_newCardModel, p_newCardModId, p_newSWVersionId,p_newSWVersion,p_newCardModelFamille,p_hwVersion,
						'WARNING: TST ferme non present pour nouvelle ' || p_newCardModel ||'/' || p_newSWVersion || ':' || tstName,
  			0);
		
		-- fin FOR
	END LOOP;
	
	RETURN 0;
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_updateatmprofileformrtasv;
--/
CREATE FUNCTION braproc_updateatmprofileformrtasv ()  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
                curs1 refcursor;
                w_id_TS INT;
                w_id_old_ATM_PROFIL INT;
                w_id_new_ATM_PROFIL INT;
        BEGIN

                OPEN curs1 FOR SELECT id_TS, id_old_ATM_PROFIL, id_new_ATM_PROFIL FROM tempIdOldNewTS;

                LOOP
                        FETCH NEXT FROM curs1 INTO w_id_TS, w_id_old_ATM_PROFIL, w_id_new_ATM_PROFIL;
                        EXIT WHEN NOT FOUND;

                        UPDATE t_mrt_access_service_vers set atpr_id = w_id_new_ATM_PROFIL
                        where mrsv_id in ( select mrsv_id from t_epc_vers_comps where stco_id = w_id_TS)
                        and atpr_id = w_id_old_ATM_PROFIL;

                END LOOP;

                CLOSE curs1;

        END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_updateshelfmodelportcount;
--/
CREATE FUNCTION braproc_updateshelfmodelportcount ()  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
                curs1 refcursor;
 				w_id_SHM INT;
                w_calculated_port_count INT;
        BEGIN

                OPEN curs1 FOR SELECT id_SHM, calculated_port_count FROM tempShlfModelPortCount;

                LOOP
                        FETCH NEXT FROM curs1 INTO w_id_SHM, w_calculated_port_count;
                        EXIT WHEN NOT FOUND;

                        UPDATE t_shelf_models set shmd_port_count = w_calculated_port_count
                        where shmd_id = w_id_SHM;

                END LOOP;

                CLOSE curs1;

        END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_updnamecartes;
--/
CREATE FUNCTION braproc_updnamecartes ()  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 
		w_count_lignes			INTEGER;
		w_cmod_name				CHAR(50);
		w_new_cmod_name			CHAR(50);
		w_cardNumber			INTEGER;
		w_ligne  				RECORD;

BEGIN	 
	
	w_count_lignes	= 0;
	SELECT	count(*) INTO w_count_lignes FROM updNameCartesInputTable;

	IF (w_count_lignes = 0) THEN
		INSERT INTO updNameCartesLogTableErr
		VALUES(null,null, 'KO', 'Fichier vide', '1');				 
	END IF;

	--
	-- parcourir les lignes de la table
	--
  	FOR w_ligne IN SELECT cmod_name, new_cmod_name FROM updNameCartesInputTable 
  	LOOP
		BEGIN
		--
		-- initialisation des informations de la carte
		--

		w_cmod_name			:= w_ligne.cmod_name;
		w_new_cmod_name		:= w_ligne.new_cmod_name;
		
		--
		-- validation de la ligne
		--
		
		IF((w_cmod_name IS NULL) OR (w_new_cmod_name IS NULL))  THEN
			INSERT INTO updNameCartesLogTableErr VALUES(w_cmod_name, w_new_cmod_name, 'KO', 'Format de la ligne dans le fichier incorrect', '2');				 
			CONTINUE;
		END IF;
				
		--
		-- recherche et validation des informations initiales de la carte
		--		
			
		 w_cardNumber = 0;
		
		SELECT	count(*)
		INTO	w_cardNumber
		FROM	t_card_models cm
		WHERE	cm.cmod_name = w_cmod_name;	
									
		IF	w_cardNumber = 0
		
		THEN
			INSERT INTO updNameCartesLogTableErr VALUES(w_cmod_name, w_new_cmod_name, 'KO', 'Modèle de carte inexistante', '3');	
			CONTINUE;
		END IF;
		
		IF	w_cardNumber > 1
		THEN
			INSERT INTO updNameCartesLogTableErr VALUES(w_cmod_name, w_new_cmod_name, 'KO', 'Plusieurs modèle de cartes trouvées', '4');
			 	
			CONTINUE;
		END IF;	
		
		UPDATE t_card_models SET cmod_name = w_new_cmod_name WHERE cmod_name = w_cmod_name;

		INSERT INTO updNameCartesLogTableErr VALUES(w_cmod_name, w_new_cmod_name, 'OK', 'Mise à jour du nom court de la carte OK', '99'); 		
 		  		
		EXCEPTION
			WHEN OTHERS THEN
				INSERT INTO updNameCartesLogTableErr VALUES(w_cmod_name, w_new_cmod_name,'KO', SQLERRM, SQLSTATE);
				CONTINUE;
		END;
		
	-- fin FOR
	END LOOP; 
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_upduntagged;
--/
CREATE FUNCTION braproc_upduntagged (p_sense smallint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE

	w_tcsvId				BIGINT;
	w_currentService		CHAR(50);
	
BEGIN
	
	RAISE NOTICE 'Valeur du p_sense : %.',p_sense;
	--
	-- Parcourir les lignes de la table
	FOR w_currentService IN SELECT serviceName FROM t_tmp_updUntagged_inputData 
  	LOOP
  	
  		--
  		-- ContrÃ´le 1 : VÃ©rification du format de la ligne
  		--
  		RAISE NOTICE 'w_currentService = % , VÃ©rification du format de la ligne.',w_currentService;
  		IF w_currentService = '' OR w_currentService LIKE '%|%' THEN
			INSERT INTO t_tmp_updUntagged_errors VALUES(w_currentService, 'Format de la ligne incorrect', '1');
  			CONTINUE;
		END IF;
  	
  		--
  		-- ContrÃ´le 2 : VÃ©rification de l'existence du service technique
  		--
  		RAISE NOTICE 'w_currentService = % , VÃ©rification de l''existence du service technique.',w_currentService;
  		w_tcsvId := null;
  		
  		SELECT tcsv_id
  		INTO w_tcsvId
  		FROM t_tech_services
  		WHERE tcsv_name = w_currentService;
  		
  		IF w_tcsvId IS NULL THEN
  			INSERT INTO t_tmp_updUntagged_errors VALUES(w_currentService, 'Service technique inexistant', '2');
  			CONTINUE;
  		END IF;
  		
  		RAISE NOTICE 'w_currentService = % , L''id du service technique est : %.',w_currentService,w_tcsvId;
  		--
  		-- Mettre Ã  jour du champ tcsv_untagged 
  		--
  		RAISE NOTICE 'w_currentService = % , Mettre Ã  jour du champ tcsv_untagged.',w_currentService;
  		UPDATE t_tech_services
  		SET tcsv_untagged = p_sense
  		WHERE tcsv_id = w_tcsvId;
  		
  		INSERT INTO t_tmp_updUntagged_errors VALUES(w_currentService, 'Mettre Ã  jour du champ tcsv_untagged OK', '0');
  		
  	-- fin FOR
	END LOOP; 
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_upgrademapping;
--/
CREATE FUNCTION braproc_upgrademapping ()  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE
	w_temp_new_mapping_release		character(12);
BEGIN 
	SELECT apcf_release 
	INTO w_temp_new_mapping_release 
	FROM applicationConfigsTempTable
	WHERE apcf_component_name = 'Mapping Cible';
	
	UPDATE t_application_configs 
	SET apcf_release = w_temp_new_mapping_release
	WHERE apcf_component_name = 'Mapping';
	RETURN 0;													
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION braproc_verifymapping;
--/
CREATE FUNCTION braproc_verifymapping (p_isdowngrademapping integer)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE 
		w_data_base_release 	character(12);
		w_mapping_release		character(12);
		w_temp_data_base_release 	character(12);
		w_temp_mapping_release		character(12);
		w_temp_mapping_cible_release    character(12);
BEGIN
	SELECT apcf_release 
	INTO w_temp_data_base_release 
	FROM applicationConfigsTempTable 
	WHERE apcf_component_name = 'Base de donnees';
	
	SELECT apcf_release 
	INTO w_temp_mapping_release 
	FROM applicationConfigsTempTable 
	WHERE apcf_component_name = 'Mapping';
	
	SELECT apcf_release
    INTO w_temp_mapping_cible_release
    FROM applicationConfigsTempTable
    WHERE apcf_component_name = 'Mapping Cible';
        
	SELECT apcf_release 
	INTO w_data_base_release 
	FROM t_application_configs 
	WHERE apcf_component_name = 'Base de donnees';
	
	SELECT apcf_release 
	INTO w_mapping_release 
	FROM t_application_configs 
	WHERE apcf_component_name = 'Mapping';
	
	IF (p_isDowngradeMapping = 0 AND 
	    (w_mapping_release IS DISTINCT FROM  w_temp_mapping_release)
	   )
	OR
	   (p_isDowngradeMapping = 1 AND 
	    w_mapping_release IS DISTINCT FROM  w_temp_mapping_cible_release
	   )
	THEN
		INSERT INTO upgradeMappingLogTableErr 
		(str_error)
		VALUES ('Le fichier de mapping n`est pas compatible avec le mapping actuelle de la base');
	END IF;
RETURN 0;														
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_addfreevciforvp;
--/
CREATE FUNCTION brasil_addfreevciforvp (p_idvp bigint, p_bemerk2 brasiltype_bemerk, p_vcimin integer, p_nbnewvci integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nbVciInserted INT;
	w_vciMinForIns INT;
	w_vciMaxForIns INT;
	w_row RECORD;

BEGIN
	IF (p_vciMin < p_bemerk2.vc_min) THEN
			PERFORM brasil_raiseException(11, '1');
	END IF;

	IF (p_vciMin > p_bemerk2.vc_max) THEN
			PERFORM brasil_raiseException(11, '2');
	END IF;

	w_nbVciInserted := 0;
	
	
	w_vciMinForIns := p_vciMin;

	FOR w_row IN SELECT vckr_vc_min, vckr_vc_max FROM t_vc_lock_ranges  where rpct_id=p_idVP ORDER BY vckr_vc_min ASC
	LOOP
		w_vciMaxForIns := w_row.vckr_vc_min -1;
		w_nbVciInserted := brasil_insert_vci(p_idVP, w_nbVciInserted, w_vciMinForIns, w_vciMaxForIns, p_nbNewVci);
	
		IF (w_nbVciInserted = p_nbNewVci)THEN
			EXIT;
		END IF;
		
		w_vciMinForIns := w_row.vckr_vc_max + 1;
		--RETURN NEXT w_row;
	END LOOP;
				
	w_vciMaxForIns := p_bemerk2.vc_max;
	IF (w_nbVciInserted < p_nbNewVci)THEN
		w_nbVciInserted := brasil_insert_vci(p_idVP, w_nbVciInserted, w_vciMinForIns, w_vciMaxForIns, p_nbNewVci);
	END IF;
				
	

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_addsupfreevciforvp;
--/
CREATE FUNCTION brasil_addsupfreevciforvp (p_idvp bigint, p_bemerk2 brasiltype_bemerk, p_currthreshold integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nbVciInserted INT;
	w_vciMinForIns INT;
	w_vciMaxForIns INT;
	w_row RECORD;
	w_nbOccupiedVci INT;
	w_nbFreeVC INT;

BEGIN
	
	SELECT COUNT(rscv_vci) FROM t_d_rsc_vcis INTO w_nbOccupiedVci WHERE rpct_id = p_idVP AND rscv_status != 'F';

	w_nbFreeVC := p_currThreshold - w_nbOccupiedVci;
	w_nbVciInserted := 0;
	
	w_vciMinForIns := p_bemerk2.vc_min;
	--w_vciMinForIns := p_vciMin;

	FOR w_row IN SELECT vckr_vc_min, vckr_vc_max FROM t_vc_lock_ranges  where rpct_id=p_idVP ORDER BY vckr_vc_min ASC
	LOOP
		w_vciMaxForIns := w_row.vckr_vc_min -1;
		w_nbVciInserted := brasil_insert_vci(p_idVP, w_nbVciInserted, w_vciMinForIns, w_vciMaxForIns, w_nbFreeVC);
	
		IF (w_nbVciInserted = w_nbFreeVC)THEN
			EXIT;
		END IF;
		
		w_vciMinForIns := w_row.vckr_vc_max + 1;
		--RETURN NEXT w_row;
	END LOOP;
				
	w_vciMaxForIns := p_bemerk2.vc_max;
	IF (w_nbVciInserted < w_nbFreeVC)THEN
		w_nbVciInserted := brasil_insert_vci(p_idVP, w_nbVciInserted, w_vciMinForIns, w_vciMaxForIns, w_nbFreeVC);
	END IF;
				
	

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_checkafterupdateresource;
--/
CREATE FUNCTION brasil_checkafterupdateresource (p_idvp bigint, p_newserialno integer, p_newsuppresspl smallint, p_oldbemerk2 brasiltype_bemerk, p_newbemerk2 brasiltype_bemerk, p_oldstocksize integer, p_oldcurrthreshold integer, p_oldoccupiedcount integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_oldNbVcMax INT;

	w_delta INT;
	w_NbVcToAdd INT;

	w_newNbVcMax INT;
	w_newStockSize INT;
	w_newCurrThreshold INT;

	w_needToReinit INT;
	
	FREE_VC_EXTENDS INT;
BEGIN
	w_needToReinit := 0;

	w_newNbVcMax := CASE WHEN p_newSuppressPl = 1 THEN brasil_min(p_newBemerk2.allocated_vc_count, p_newSerialNo) ELSE p_newBemerk2.allocated_vc_count END;
	w_oldNbVcMax := p_oldStockSize + p_oldCurrThreshold;

	w_delta := w_newNbVcMax - w_oldNbVcMax;

	-- La reserve grandit alors qu'il n'y en avait plus => allocation immédiate de Vc
	IF (w_delta >= 0 AND p_oldStockSize = 0) THEN

		SELECT brasil_free_vc_extends() INTO FREE_VC_EXTENDS;
		w_NbVcToAdd := brasil_min(FREE_VC_EXTENDS, w_delta);
		w_newStockSize := p_oldStockSize + w_delta - w_NbVcToAdd;
		w_newCurrThreshold := p_oldCurrThreshold + w_NbVcToAdd;

		-- remarque: risque de réaprovisionnement en double au cas où needNewVc déjà setté.

		w_needToReinit := 1;

	-- La reserve change sans devenir négative
	ELSIF (p_oldStockSize + w_delta >= 0) THEN

		w_newStockSize := p_oldStockSize + w_delta;
		w_newCurrThreshold := p_oldCurrThreshold;

	-- Il va falloir retirer des vci qui etaient proposes
	ELSE

		-- Il y a plus de vc alloues que le nombre total de vc dispo
		IF (p_oldOccupiedCount > w_newNbVcMax) THEN
			PERFORM brasil_raiseException(11, '6');
		END IF;

		w_newStockSize := 0;
		w_newCurrThreshold := w_newNbVcMax;

		w_needToReinit := 1;

	END IF;

	UPDATE t_d_controlable_rscs
		SET	ctrs_stock_size = w_newStockSize,
			ctrs_curr_threshold = w_newCurrThreshold
		WHERE rpct_id = p_idVP;

	IF (p_oldBemerk2 IS DISTINCT FROM p_newBemerk2) THEN
		PERFORM brasil_checkOccupiedVci(p_idVp, p_newBemerk2);
		w_needToReinit := 1;
	END IF;

	IF (w_needToReinit = 1) THEN
		PERFORM brasil_initFreeVciForVp(p_idVP, p_newBemerk2, w_newCurrThreshold);
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_checkoccupiedvci;
--/
CREATE FUNCTION brasil_checkoccupiedvci (p_idvp bigint, p_newbemerk2 brasiltype_bemerk)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_row RECORD;

	w_vcMin INT;
	w_vcMax INT;

	w_nbPlage INT;
	w_numPlage INT;
	w_id BIGINT;
BEGIN
	w_vcMin := p_newBemerk2.vc_min;
	w_vcMax := p_newBemerk2.vc_max;
	w_nbPlage := p_newBemerk2.nb_locked_ranges;
	FOR w_row IN SELECT rscv_vci FROM t_d_rsc_vcis WHERE rpct_id = p_idVp AND rscv_status IN ('O', 'R', 'C')
	LOOP
		-- vci non compris entre vcmin et vcmax
		IF (w_row.rscv_vci < w_vcMin OR w_row.rscv_vci > w_vcMax) THEN
			PERFORM brasil_raiseException(11, '4');
		END IF;

		IF (w_nbPlage != 0) THEN
			-- vci appartient a une plage bloquee
			SELECT rpct_id FROM t_vc_lock_ranges INTO w_id WHERE rpct_id = p_idVp AND w_row.rscv_vci >= vckr_vc_min AND w_row.rscv_vci <= vckr_vc_max;
			IF (FOUND) THEN
				PERFORM brasil_raiseException(11, '5');
			END IF;
		END IF;
	END LOOP;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_free_vc;
--/
CREATE FUNCTION brasil_free_vc ()  RETURNS integer
  IMMUTABLE
AS $dbvis$
BEGIN
    RETURN 200;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_free_vc_extends;
--/
CREATE FUNCTION brasil_free_vc_extends ()  RETURNS integer
  IMMUTABLE
AS $dbvis$
BEGIN
    RETURN 200;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_initfreevciforvp;
--/
CREATE FUNCTION brasil_initfreevciforvp (p_idvp bigint, p_bemerk2 brasiltype_bemerk, p_currthreshold integer)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	-- Suppression des vci libres de la ressources
	DELETE FROM t_d_rsc_vcis WHERE rpct_id = p_idVP AND rscv_status = 'F';
	PERFORM brasil_addSupFreeVciForVp(p_idVP, p_bemerk2, p_currThreshold);

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_insert_vci;
--/
CREATE FUNCTION brasil_insert_vci (p_idvp bigint, p_nbvciinserted integer, p_vciminforins integer, p_vcimaxforins integer, p_nbnewvci integer)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE
	w_rpct_id bigint;
BEGIN
    IF (p_vciMinForIns <= p_vciMaxForIns) THEN
		FOR i IN p_vciMinForIns..p_vciMaxForIns LOOP
 
			SELECT rpct_id FROM t_d_rsc_vcis INTO w_rpct_id WHERE rpct_id = p_idVP AND rscv_vci = i;
			
			-- Si le Vci fait partie des Vci déjà occupés, alors on insert pas
			IF(NOT FOUND) THEN
				INSERT INTO t_d_rsc_vcis(rpct_id, rscv_vci, rscv_status)
				VALUES(	p_idVP,
						i,
						'F'::CHAR(1));
				p_nbVciInserted := p_nbVciInserted + 1;
				-- Si on a atteint le quota, on sort
				IF (p_nbVciInserted = p_nbNewVci)THEN
					EXIT;
				END IF;
			END IF;
		END LOOP;
	END IF;
	RETURN p_nbVciInserted;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_min;
--/
CREATE FUNCTION brasil_min (p_a integer, p_b integer)  RETURNS integer
  VOLATILE
AS $dbvis$
BEGIN
	IF (p_a < p_b) THEN
		RETURN p_a;
	ELSE
		RETURN p_b;
	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_min_free_vc_count;
--/
CREATE FUNCTION brasil_min_free_vc_count ()  RETURNS integer
  IMMUTABLE
AS $dbvis$
BEGIN
    RETURN 50;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_raiseexception;
--/
CREATE FUNCTION brasil_raiseexception (p_code integer, p_message character)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	RAISE EXCEPTION 'TR_BRASIL%', p_message;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_updateallocablevc_lockedrange;
--/
CREATE FUNCTION brasil_updateallocablevc_lockedrange (p_idrsc bigint)  RETURNS brasiltype_bemerk
  VOLATILE
AS $dbvis$
DECLARE
	w_nbPlageBloque SMALLINT;
	w_nbVcBloque INT;
	w_bemerk BrasilType_Bemerk;
	w_allocables_vc_count INT;

BEGIN
	SELECT COALESCE(sum(vckr_vc_max - vckr_vc_min +1),0) INTO w_nbVcBloque  FROM t_vc_lock_ranges l WHERE l.rpct_id =p_idRsc;
	SELECT count(*) INTO w_nbPlageBloque FROM t_vc_lock_ranges l  WHERE l.rpct_id=p_idRsc;
	
	SELECT rpct_vc_max - rpct_vc_min - w_nbVcBloque  + 1 INTO w_allocables_vc_count FROM t_res_prod_controlables WHERE rpct_id  =p_idRsc ;
	
	UPDATE t_res_prod_controlables SET 
		rpct_nb_locked_ranges = w_nbPlageBloque,
		rpct_allocables_vc_count =  w_allocables_vc_count
	WHERE rpct_id  =p_idRsc ;
	
	w_bemerk.allocated_vc_count := w_allocables_vc_count;
	w_bemerk.nb_locked_ranges := w_nbPlageBloque;

	RETURN w_bemerk;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_updatecompteursvlan;
--/
CREATE FUNCTION brasil_updatecompteursvlan (p_rpct_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nbRU INT;

BEGIN
	RAISE NOTICE ' -------- Debut brasil_updateCompteursVlan';
	IF (p_rpct_id IS NOT NULL) THEN
		
		-- Mise à jour de ctrs_occupied_count et ctrs_used_count
		--BRASIL-440 - ini:
		--SELECT COUNT(rsus_id) FROM t_resource_usages ru2, t_mrt_access_services m2 INTO w_nbRU WHERE rpct_id=p_rpct_id AND m2.mras_id = ru2.mras_id and m2.mras_utilisation = 1;
		SELECT COUNT(rsus_id) FROM t_resource_usages ru2 JOIN t_mrt_access_services m2 ON m2.mras_id = ru2.mras_id INTO w_nbRU WHERE rpct_id=p_rpct_id and m2.mras_utilisation = 1;
		--BRASIL-440 - fin:
		UPDATE t_d_controlable_rscs SET ctrs_occupied_count = w_nbRU, ctrs_used_count= w_nbRU WHERE rpct_id = p_rpct_id;
		
		--Mise à jour de rpct_allocated_vc_count
		SELECT COUNT(rpct_id) FROM t_resource_usages INTO w_nbRU WHERE rpct_id = p_rpct_id AND mras_id IS NOT NULL;
		UPDATE t_res_prod_controlables SET rpct_allocated_vc_count = w_nbRU WHERE rpct_id = p_rpct_id;
	END IF;
	RAISE NOTICE ' -------- Fin brasil_updateCompteursVlan';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_updatecompteursvpniveauvc;
--/
CREATE FUNCTION brasil_updatecompteursvpniveauvc (p_rpct_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nb INT;
BEGIN
	IF (p_rpct_id IS NOT NULL) THEN
		SELECT COUNT(*) FROM t_d_rsc_vcis INTO w_nb WHERE rpct_id=p_rpct_id AND rscv_status IN ('R','O','C');
		RAISE NOTICE ' brasil_updateCompteursVpNiveauVc -------- p_rpct_id : %, w_nb : %',p_rpct_id,w_nb;
		-- Mise à jour de ctrs_occupied_count
		UPDATE t_d_controlable_rscs SET ctrs_occupied_count = w_nb WHERE rpct_id = p_rpct_id;
		
		--Mise à jour de rpct_allocated_vc_count
		UPDATE t_res_prod_controlables SET rpct_allocated_vc_count = w_nb WHERE rpct_id = p_rpct_id;
	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION brasil_updatecompteursvpniveauvp;
--/
CREATE FUNCTION brasil_updatecompteursvpniveauvp (p_rpct_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nb INT;
BEGIN
	IF (p_rpct_id IS NOT NULL) THEN
		SELECT COUNT(*) FROM t_resource_usages INTO w_nb WHERE rpct_id=p_rpct_id;
		-- Mise à jour de ctrs_occupied_count
		UPDATE t_d_controlable_rscs SET ctrs_occupied_count = w_nb WHERE rpct_id = p_rpct_id;
		
		--Mise à jour de rpct_allocated_vc_count
		UPDATE t_res_prod_controlables SET rpct_allocated_vc_count = w_nb WHERE rpct_id = p_rpct_id;
	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION count_em_all;
--/
CREATE FUNCTION count_em_all ()  RETURNS SETOF table_count
  VOLATILE
AS $dbvis$
DECLARE 
    the_count RECORD; 
    t_name RECORD; 
    r table_count%ROWTYPE; 

BEGIN
    FOR t_name IN 
        SELECT table_schema,table_name
        FROM information_schema.tables
        where table_schema !='pg_catalog'
          and table_schema !='information_schema'
        ORDER BY 1,2
        LOOP
            FOR the_count IN EXECUTE 'SELECT COUNT(*) AS "count" FROM ' || t_name.table_schema||'.'||t_name.table_name
            LOOP 
            END LOOP; 

            r.table_schema := t_name.table_schema;
            r.table_name := t_name.table_name; 
            r.num_rows := the_count.count; 
            RETURN NEXT r; 
        END LOOP; 
        RETURN; 
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION explain_query;
--/
CREATE FUNCTION explain_query (query text)  RETURNS TABLE(plan text)
  VOLATILE
AS $dbvis$
DECLARE
    clean_query text;
    current_pos integer := 1;
    match_pos integer;
    column_info record;
    table_column text;
    for_update_part text;
    main_query_part text;
    tables_list text;
    table_aliases text[];
    i integer;
BEGIN
    clean_query := query;
    
    -- Extraire les alias de tables
    table_aliases := ARRAY(
        SELECT DISTINCT matches[2]
        FROM regexp_matches(clean_query, 
                          '(\w+)\s+(?:as\s+)?(\w+)(?=\s+(?:inner\s+)?join|\s+on|\s+where|\s*$)', 
                          'gi') AS matches
    );

    -- Séparer la partie principale de la requête et la partie FOR UPDATE
    IF position('FOR UPDATE OF' in upper(clean_query)) > 0 THEN
        main_query_part := substring(clean_query from 1 for position('FOR UPDATE OF' in upper(clean_query)) - 1);
        for_update_part := substring(clean_query from position('FOR UPDATE OF' in upper(clean_query)));
        
        -- Extraire et nettoyer la liste des tables
        tables_list := substring(for_update_part from 'OF\s+(.*)$');
        tables_list := regexp_replace(tables_list, 'OF\s+', '');
        
        -- Remplacer les noms de tables par leurs alias s'ils existent
        FOR i IN 1..array_length(table_aliases, 1) LOOP
            tables_list := regexp_replace(tables_list, 
                                        't_\w+', 
                                        table_aliases[i], 
                                        'g');
        END LOOP;
        
        tables_list := replace(tables_list, '|', ', ');
        
        -- Reconstruire la clause FOR UPDATE
        clean_query := main_query_part || 'FOR UPDATE OF ' || tables_list;
    END IF;

    -- Traiter les paramètres ?
    WHILE position('?' in substring(clean_query from current_pos)) > 0 LOOP
        match_pos := current_pos + position('?' in substring(clean_query from current_pos)) - 1;
        
        WITH RECURSIVE extracted AS (
            SELECT substring(clean_query from match_pos - 50 for 50) as txt
        )
        SELECT COALESCE(
            (SELECT (regexp_matches(txt, '(\w+\.\w+)\s*[=><]\s*$'))[1] 
             FROM extracted),
            'default.default'
        ) INTO table_column;

        BEGIN
            SELECT a.attname, format_type(a.atttypid, a.atttypmod) as type
            INTO column_info
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname = split_part(table_column, '.', 1)
            AND a.attname = split_part(table_column, '.', 2)
            AND a.attnum > 0;
        EXCEPTION WHEN OTHERS THEN
            column_info := NULL;
        END;

        IF column_info IS NOT NULL AND column_info.type LIKE '%int%' THEN
            clean_query := overlay(clean_query placing '1' from match_pos for 1);
        ELSIF column_info IS NOT NULL AND column_info.type LIKE '%char%' THEN
            clean_query := overlay(clean_query placing '''dummy''' from match_pos for 1);
        ELSE
            clean_query := overlay(clean_query placing '''1''' from match_pos for 1);
        END IF;

        current_pos := match_pos + 1;
    END LOOP;

    RAISE NOTICE 'Clean query: %', clean_query;

    IF clean_query ILIKE 'SELECT%' THEN
        RETURN QUERY EXECUTE 'EXPLAIN ' || clean_query;
    END IF;
    RETURN;
EXCEPTION 
    WHEN OTHERS THEN
        RAISE NOTICE 'Error explaining query: %', SQLERRM;
        RETURN;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION f_t_media_links_checktranslateextandupdatepointformutls;
--/
CREATE FUNCTION f_t_media_links_checktranslateextandupdatepointformutls (p_oldpcp bigint, p_newpcp bigint, p_endab bigint)  RETURNS brasiltype_addinfo[]
  VOLATILE
AS $dbvis$
DECLARE 

	w_oldEquip		BIGINT;
	w_newEquip		BIGINT;
	w_oldPogr_name CHAR(3);
	w_oldPogr_management_policy CHAR(1);
	w_oldPogr_group_type  CHAR(1);
	--w_oldPort_quality CHAR(1);
	w_oldPogr_id BIGINT;
	w_newPogr_name CHAR(3);
	w_newPogr_management_policy CHAR(1);
	w_newPogr_group_type  CHAR(1);
	--w_newPort_quality CHAR(1);
	w_newPogr_id BIGINT;
	w_row RECORD;

	w_oldRetour		BrasilType_AddInfo;
	w_newRetour		BrasilType_AddInfo;
	w_retour BrasilType_AddInfo[];
	w_pos	INT;
BEGIN
	-- Infos sur les pcp
	SELECT	p.card_id, gr.pogr_name, gr.pogr_management_policy, gr.pogr_group_type, gr.pogr_id

	INTO	w_oldEquip, w_oldPogr_name, w_oldPogr_management_policy, w_oldPogr_group_type,w_oldPogr_id
		
	FROM	t_ports p LEFT JOIN t_port_groups gr ON p.pogr_id = gr.pogr_id
	WHERE	p.port_id = p_oldPCP;

	-- Le point n'existe pas
	IF (w_oldEquip IS NULL) THEN
		PERFORM brasil_raiseException(11,'98');
	END IF;

	SELECT	p.card_id, gr.pogr_name, gr.pogr_management_policy, gr.pogr_group_type, gr.pogr_id

	INTO	w_newEquip, w_newPogr_name, w_newPogr_management_policy, w_newPogr_group_type,w_newPogr_id
		
	FROM	t_ports p LEFT JOIN t_port_groups gr ON p.pogr_id = gr.pogr_id
	WHERE	p.port_id = p_newPCP;

	-- Le point n'existe pas
	IF (w_newEquip IS NULL) THEN
		PERFORM brasil_raiseException(11, '99');
	END IF;

	-- les ports source et cible doivent avoir le même type d'usage
	IF w_newPogr_management_policy != w_oldPogr_management_policy
	THEN
		PERFORM brasil_raiseException(11, '96');
	END IF;

	-- le port p_oldPCP est isolé, on retourne p_newPCP lui-même
	IF (w_oldPogr_id IS NULL )
	THEN
		--w_oldRetour := p_oldPCP::CHAR(9) || 'P   ';
		w_oldRetour.port_id := p_oldPCP;
		w_oldRetour.typeExtPhys := 'P';
		--w_newRetour := ' ';

	-- le port est dans un groupe réel
	ELSIF (w_oldPogr_management_policy = 'G') THEN

		-- Peuplement de la table des PCP des groupes pour mutation ultérieure des liens
		w_pos := 1;
		FOR w_row IN SELECT p.port_id, p.port_occup_ont, p.port_logical_occup_cpt, p.port_num FROM t_ports p 
		WHERE  p.pogr_id = w_oldPogr_id
		--AND card_id = w_oldEquip AND gr.pogr_name=w_oldPogr_name AND gr.pogr_management_policy = w_oldPogr_management_policy
		ORDER by 4
		LOOP
			
			INSERT INTO GroupedPCP VALUES(w_row.port_id, w_row.port_occup_ont, w_row.port_logical_occup_cpt, w_pos, p_endAB, 1);
			w_pos := w_pos + 1;
		END LOOP;
		
		/*FOREACH c1 FOR
			SELECT	id, updateCounter,
				X3010_13_intval, X3029_16_mychars[2,6], SUBSTR(TRIM(X3010_2_mychars), -3)
			INTO	w_id, w_uc,
				w_usageCounter, w_logUsageCounter, w_poa
			FROM	$EMS1DB:PCP
			WHERE	X3029_8_cmEquip = w_oldEquip
			AND	X3029_17_mychars[1,4] = w_oldSpeed[1,4]
			ORDER	BY 5

			INSERT INTO GroupedPCP VALUES(w_id, w_uc, w_usageCounter, w_logUsageCounter, w_pos, p_endAB, 1);
			LET w_pos = w_pos + 1;
		END FOREACH;*/

		w_pos := 1;
		FOR w_row IN SELECT p.port_id, p.port_occup_ont, p.port_logical_occup_cpt, p.port_num FROM t_ports p JOIN t_port_groups gr ON p.pogr_id = gr.pogr_id
		WHERE  p.pogr_id = w_newPogr_id AND gr.pogr_group_type = w_oldPogr_group_type AND p.port_occup_ont = 0
		ORDER by 4
		LOOP
			
			INSERT INTO GroupedPCP VALUES(w_row.port_id, w_row.port_occup_ont, w_row.port_logical_occup_cpt, w_pos, p_endAB, 0);
			w_pos := w_pos + 1;
		END LOOP;
		
		/*w_pos := 1;
		FOREACH c2 FOR
			SELECT	id, updateCounter,
				X3010_13_intval, X3029_16_mychars[2,6], SUBSTR(TRIM(X3010_2_mychars), -3)
			INTO	w_id, w_uc,
				w_usageCounter, w_logUsageCounter, w_poa
			FROM	$EMS1DB:PCP
			WHERE	X3029_8_cmEquip = w_newEquip
			AND	X3029_17_mychars[1,4] = w_newSpeed[1,4]
			AND	X3029_17_mychars[6] = w_oldSpeed[6]	-- le type cible doit être égal au type source
			AND	X3010_13_intval = 0		-- les ports cible doivent être entièrement libres
			ORDER	BY 5

			INSERT INTO GroupedPCP VALUES(w_id, w_uc, w_usageCounter, w_logUsageCounter, w_pos, p_endAB, 0);
			LET w_pos = w_pos + 1;
		END FOREACH;*/

		-- Controle des pré-requis sur les groupes sources et cibles
		--  + même cardinalité
		--  + même type (cf. peuplement de la table ci-dessus)
		--  + cible entièrement libre (cf. peuplement de la table ci-dessus)
		IF ((SELECT COUNT(*) FROM GroupedPCP WHERE isSource = 1 AND endAB = p_endAB)
		    !=
		    (SELECT COUNT(*) FROM GroupedPCP WHERE isSource = 0 AND endAB = p_endAB))
		THEN
			PERFORM brasil_raiseException(11, '97');
		END IF;

		-- Mise à jour des ports source (libération)
		--BRASIL-440 - ini:
		--UPDATE	t_ports p
		--SET	port_occup_ont = cible.usageCounter, port_logical_occup_cpt = cible.logUsageCounter 
		--FROM GroupedPCP source, GroupedPCP cible
		--WHERE	source.pcp_id = p.port_id
		--AND	source.isSource = 1
		--AND	cible.isSource = 0
		--AND	cible.endAB = source.endAB
		--AND	cible.position = source.position;
		
		UPDATE t_ports p
		   SET port_occup_ont = cible.usageCounter, port_logical_occup_cpt = cible.logUsageCounter 
		  FROM GroupedPCP source JOIN GroupedPCP cible ON (source.pcp_id = p.port_id AND cible.endAB = source.endAB AND cible.position = source.position)
		 WHERE source.isSource = 1
		   AND cible.isSource = 0;
		--BRASIL-440 - fin:

		-- Mise à jour des ports cible (occupation)
		--BRASIL-440 - ini:
		--UPDATE	t_ports p
		--SET	port_occup_ont = source.usageCounter, port_logical_occup_cpt = source.logUsageCounter 
		--FROM	GroupedPCP cible, GroupedPCP source
		--WHERE	cible.pcp_id = p.port_id
		--AND	cible.isSource = 0
		--AND	source.isSource = 1
		--AND	source.endAB = cible.endAB
		--AND	source.position = cible.position;
		UPDATE t_ports p
		   SET port_occup_ont = source.usageCounter, port_logical_occup_cpt = source.logUsageCounter 
		  FROM GroupedPCP cible
		  JOIN GroupedPCP source ON (cible.pcp_id = p.port_id AND source.endAB = cible.endAB AND source.position = cible.position)
		 WHERE cible.isSource = 0
		   AND source.isSource = 1;
		--BRASIL-440 - fin:

		-- Construction de l'ExtGroupe a retourner pour pouvoir muter les ressources logiques ...
		--w_oldRetour := w_oldEquip::CHAR(9) || 'G' || w_oldPogr_name;
		w_oldRetour.pogr_id := w_oldPogr_id;
		w_oldRetour.typeExtPhys := 'G';
		
		--w_newRetour := w_newEquip::CHAR(9) || 'G' || w_newPogr_name;
		w_newRetour.pogr_id := w_newPogr_id;
		w_newRetour.typeExtPhys := 'G';

	-- le port est dans un groupe liste : on ne gère pas
	ELSE
		PERFORM brasil_raiseException(11, '95');
	END IF;

	w_retour[0] := w_oldRetour;
	w_retour[1] := w_newRetour;
	RETURN w_retour;
	--RETURN w_oldRetour, w_newRetour;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION f_t_mrt_access_dslams_ptsextmrtdslam;
--/
CREATE FUNCTION f_t_mrt_access_dslams_ptsextmrtdslam (p_oldaddinfo brasiltype_addinfo, p_newaddinfo brasiltype_addinfo, p_mrtd_info_portgp_tmp character)  RETURNS bigint
  VOLATILE
AS $dbvis$
DECLARE
	w_pogr_id BIGINT := 0;
	w_typeExtA CHAR(1);
	w_typeInterfA CHAR(1);
BEGIN

	IF (NOT(p_newAddInfo IS NULL)) THEN
		IF (p_oldAddInfo.typeInterface = '' OR p_oldAddInfo IS NULL OR (p_oldAddInfo.port_id IS NULL AND p_oldAddInfo.pogr_id IS NULL)) THEN

			w_typeExtA = p_newAddInfo.typeExtPhys;
			w_typeInterfA = p_newAddInfo.typeInterface;

			-- L'extA peut être utilisee au plus par un lien support
			-- L'extA n'a aucun occupant, les ports Xdsl ne sont pas occupés par des liens supports
			-- Donc, on verifie seulement si le point a déjà un occupant lors de la mise a jour de ce dernier

			-- ExtA=ExtPort
			IF (w_typeExtA='P') THEN
				IF (w_typeInterfA = 'D') THEN
					PERFORM sp_checkAndUpdateNewP(p_newAddInfo.port_id, 0);
				-- w_typeInterfA = F
				ELSE
					PERFORM sp_checkAndUpdateNewP(p_newAddInfo.port_id, 1);
				END IF;

			-- ExtA=ExtGroupe
			ELSIF (w_typeExtA='G') THEN
				PERFORM sp_checkAndUpdateNewG(p_newAddInfo.pogr_id, 0);

			-- ExtA=ExtGroupeListe
			ELSIF (p_mrtd_info_portgp_tmp IS NOT NULL and p_mrtd_info_portgp_tmp != '') THEN
				w_pogr_id := sp_t_mrt_access_dslams_checkAndUpdateNewL(p_mrtd_info_portgp_tmp);
				-- On enleve la partie concernant les points de la liste
				-- LET w_newAddInfo= RPAD(p_newAddInfo[1,14], 160, " ");

			END IF;
		END IF;
	END IF;
/*
	IF (p_newAddInfo.typeExtPhys = 'L') THEN
		w_a_grp_type= '';
	END IF;

	RETURN w_a_grp_type;*/
	RETURN w_pogr_id;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION f_t_res_prod_controlables_getnbutil;
--/
CREATE FUNCTION f_t_res_prod_controlables_getnbutil (addinfo brasiltype_addinfo)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE
	w_nbUtilA INT := 0;
	w_nbUtilAA1 INT := 0;
	w_nbUtilAA2 INT := 0;
	w_nbUtilAB2 INT := 0;
BEGIN
	-- Verification de l'utilisation de la nouvelle extA
	-- L'extA peut être utilisee par un lien support ou par un VP avec un interfaceId different ou par autre interface

	IF (AddInfo.typeExtPhys = 'P') THEN
		-- Nb d'utilisateur de extA en ExtA, avec type = D (=0) en cas d'extremite port
		SELECT COUNT(*)  FROM t_mrt_access_dslams  INTO w_nbUtilAA1
		WHERE a_port_id = AddInfo.port_id AND mrtd_point_a_phys_end_type = 'P' AND mrtd_interface_type = 'D';
		
		-- Nb d'utilisateur de extA en ExtA, V et interfaceId egale (=0)
		SELECT COUNT(*) FROM t_res_prod_controlables INTO w_nbUtilAA2
		WHERE a_port_id  = AddInfo.port_id 
		AND  rpct_point_a_interface_type = AddInfo.typeInterface 
		AND rpct_point_a_interface_id = AddInfo.interfaceId
		AND rpct_point_a_phys_end_type = 'P';
		
		-- Nb d'utilisateur de extA en ExtB, V et interfaceId egale (=0)
		SELECT COUNT(*)  FROM t_res_prod_controlables INTO w_nbUtilAB2
		WHERE b_port_id  = AddInfo.port_id 
		AND  rpct_point_b_interface_type = AddInfo.typeInterface 
		AND rpct_point_b_interface_id = AddInfo.interfaceId
		AND rpct_point_b_phys_end_type = 'P';
		
	ELSIF (AddInfo.typeExtPhys = 'G') THEN
		-- Nb d'utilisateur de extA en ExtA, avec type = D (=0) en cas d'extremite groupe de port reel
		SELECT COUNT(*)  FROM t_mrt_access_dslams INTO w_nbUtilAA1
		WHERE a_pogr_id = AddInfo.pogr_id  AND mrtd_point_a_phys_end_type = 'G' AND mrtd_interface_type = 'D';
		
		-- Nb d'utilisateur de extA en ExtA, V et interfaceId egale (=0)
		SELECT COUNT(*)  FROM t_res_prod_controlables INTO w_nbUtilAA2
		WHERE a_pogr_id = AddInfo.pogr_id  
		AND  rpct_point_a_interface_type = AddInfo.typeInterface 
		AND rpct_point_a_interface_id = AddInfo.interfaceId
		AND rpct_point_a_phys_end_type = 'G';
		
		-- Nb d'utilisateur de extA en ExtB, V et interfaceId egale (=0)
		SELECT COUNT(*)  FROM t_res_prod_controlables INTO w_nbUtilAB2
		WHERE b_pogr_id = AddInfo.pogr_id  
		AND  rpct_point_b_interface_type = AddInfo.typeInterface 
		AND rpct_point_b_interface_id = AddInfo.interfaceId
		AND rpct_point_b_phys_end_type = 'G';
		
	
	END IF;

	w_nbUtilA = w_nbUtilAA1 + w_nbUtilAA2 + w_nbUtilAB2;
	RETURN w_nbUtilA;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION pg_stat_statements;
--/
CREATE FUNCTION pg_stat_statements (showtext boolean, OUT userid oid, OUT dbid oid, OUT queryid bigint, OUT query text, OUT calls bigint, OUT total_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision)  RETURNS SETOF record
  VOLATILE
  RETURNS NULL ON NULL INPUT
AS $dbvis$
pg_stat_statements_1_2
$dbvis$ LANGUAGE c
/
DROP FUNCTION pg_stat_statements_reset;
--/
CREATE FUNCTION pg_stat_statements_reset ()  RETURNS void
  VOLATILE
AS $dbvis$
pg_stat_statements_reset
$dbvis$ LANGUAGE c
/
DROP FUNCTION sp_brasil_addfreevciforvplist;
--/
CREATE FUNCTION sp_brasil_addfreevciforvplist ()  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_iterateNb INT;
	w_currVP BIGINT;
	w_stockSize INT;
	w_currThresHold INT;
	w_delta INT;
	w_bemerk2 BrasilType_Bemerk;
	FREE_VC_EXTENDS INT;
	w_row RECORD;
BEGIN
	-- Table qui va contenir les vp qui ont besoin de nouveaux vci
	CREATE TEMP TABLE w_needNewVcTmp(w_rscId INT);

	 w_iterateNb := 1;
	SELECT brasil_free_vc_extends() INTO FREE_VC_EXTENDS;
	-- Tant qu'il reste des ressources dans needNewVc et qu'on n'a pas fini d'iterer
	WHILE ((SELECT COUNT(*) FROM t_d_need_new_vcs) != 0 AND w_iterateNb <= 3) LOOP

		-- Recopie des vp
		INSERT INTO w_needNewVcTmp(w_rscId) SELECT rpct_id FROM t_d_need_new_vcs;

		FOR w_row IN SELECT w_rscId  FROM w_needNewVcTmp
        LOOP
        		w_currVP:= w_row.w_rscId;				
					
			BEGIN 

				SELECT ctrs_stock_size, ctrs_curr_threshold INTO w_stockSize, w_currThresHold FROM t_d_controlable_rscs WHERE rpct_id = w_currVP;
				 w_delta := brasil_min(FREE_VC_EXTENDS, w_stockSize);

				UPDATE t_d_controlable_rscs
				    SET	ctrs_curr_threshold = ctrs_curr_threshold + w_delta,
						ctrs_stock_size = ctrs_stock_size - w_delta,
						ctrs_need_new_vc = 0 
					WHERE rpct_id = w_currVP AND ctrs_stock_size = w_stockSize;

				IF (FOUND) THEN
					SELECT rpct_vc_min, rpct_vc_max, rpct_allocables_vc_count, rpct_nb_locked_ranges INTO w_bemerk2.vc_min, w_bemerk2.vc_max, w_bemerk2.allocated_vc_count, w_bemerk2.nb_locked_ranges FROM t_res_prod_controlables WHERE rpct_id = w_currVP /*AND ExternContPers.id = TCVers.X1588_2_nContainer*/;
					PERFORM brasil_addSupFreeVciForVp(w_currVP, w_bemerk2, w_currThresHold + w_delta);
					DELETE FROM t_d_need_new_vcs WHERE rpct_id = w_currVP;
				END IF;

				--COMMIT;

			EXCEPTION WHEN OTHERS THEN 
				--ROLLBACK;
			END;

		END LOOP;

		w_iterateNb := w_iterateNb + 1;

		DELETE FROM w_needNewVcTmp;
	END LOOP;

	DROP TABLE w_needNewVcTmp;



END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_checkandupdatenewg;
--/
CREATE FUNCTION sp_checkandupdatenewg (p_pogr_id bigint, p_multioccup integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 
	--nbreResult INT := 0;
	nbreUpdatedLigne INT := 0;
	
BEGIN

	IF (p_multiOccup = 0) THEN

		-- Le groupe ne doit pas avoir des occupants
		
		/*SELECT COUNT(*) INTO nbreResult FROM t_port_groups gp, t_ports p
		WHERE p.pogr_id = gp.pogr_id AND gp.pogr_id=p_pogr_id AND port_logical_occup_cpt = 0 AND gp.pogr_management_policy='G';

		-- Aucun point ne correspond au critere
		IF (nbreResult = 0) THEN
			PERFORM brasil_raiseException(11, '58');
		END IF;*/

		UPDATE t_ports
		SET port_occup_ont = port_occup_ont + 1,
			port_logical_occup_cpt = 1
		WHERE pogr_id=p_pogr_id; --port_id IN (SELECT p.port_id FROM t_port_groups gp JOIN t_ports p ON p.pogr_id = gp.pogr_id WHERE gp.pogr_id=p_pogr_id );
						  
		GET DIAGNOSTICS nbreUpdatedLigne = ROW_COUNT;
		IF (nbreUpdatedLigne=0) THEN
			PERFORM brasil_raiseException(11, '58');
		END IF;

	ELSE

		-- Le groupe ne doit pas avoir des occupants
		/*SELECT COUNT(*) INTO nbreResult FROM t_port_groups gp, t_ports p
		WHERE p.pogr_id = gp.pogr_id AND p.card_id=p_equipId AND gp.pogr_name = p_nomGroupe AND gp.pogr_management_policy='G';
		
		-- Aucun point ne correspond au critere
		IF (nbreResult = 0) THEN
			PERFORM brasil_raiseException(11, '59');
		END IF;*/

		-- Maj des points du groupe, le groupe peut deja avoir des occupants
		UPDATE t_ports
		SET port_occup_ont = port_occup_ont + 1,
			port_logical_occup_cpt = COALESCE(port_logical_occup_cpt, 0) + 1
		WHERE pogr_id = p_pogr_id;
		--port_id IN (SELECT p.port_id FROM t_port_groups gp JOIN t_ports p ON p.pogr_id = gp.pogr_id WHERE gp.pogr_id=p_pogr_id );
							
		GET DIAGNOSTICS nbreUpdatedLigne = ROW_COUNT;
		-- Au moins un point du groupe a ete supprime
		IF (nbreUpdatedLigne=0) THEN
			PERFORM brasil_raiseException(11, '59');
		END IF;

	END IF;
	

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_checkandupdatenewp;
--/
CREATE FUNCTION sp_checkandupdatenewp (p_idpoint bigint, p_multioccup integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	nbreUpdatedLigne INT := 0;
BEGIN
	IF (p_multiOccup = 0) THEN
		-- Mise é jour du point (il ne peut pas etre multi-occupe)
		UPDATE t_ports SET port_occup_ont = port_occup_ont + 1, port_logical_occup_cpt = 1
		WHERE port_id = p_idPoint AND (port_logical_occup_cpt = 0 OR port_logical_occup_cpt IS NULL);

	ELSE
		-- Mise é jour du point (il peut etre multi-occupe)
		UPDATE t_ports SET port_occup_ont = port_occup_ont + 1, port_logical_occup_cpt = COALESCE(port_logical_occup_cpt, 0) + 1
		WHERE port_id=p_idPoint AND pogr_id IS NULL;
	END IF;

	-- Le point n'existe pas ou est deja occupe via un G ou est multi-occupe
	GET DIAGNOSTICS nbreUpdatedLigne = ROW_COUNT;
	IF (nbreUpdatedLigne = 0) THEN
		PERFORM brasil_raiseException(11, '57');
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_getdistributorstatistics;
--/
CREATE FUNCTION sp_getdistributorstatistics (id_distrib integer)  RETURNS SETOF brasiltype_distributorstatistics
  VOLATILE
AS $dbvis$
DECLARE 
	_result BrasilType_DistributorStatistics;
	enreg RECORD;
BEGIN
   FOR enreg IN SELECT strp_id, strp_name FROM t_stripes  where dist_id = ID_DISTRIB
   LOOP
   		_result.id := enreg.strp_id;
   		_result.nom := enreg.strp_name;
   		-- OCCUPE
   		select count(port_id) from t_ports INTO _result.occupe  where strp_id=_result.id and port_occupation_status = 2 and card_id is not null;
        -- OUVERT
    	select count(port_id) from t_ports  INTO _result.ouvert where strp_id=_result.id and port_attribuable = 1 and port_occupation_status != 2 and card_id is not null;
        -- RESERVE
    	select count(port_id) from t_ports  INTO _result.reserve where strp_id=_result.id and port_attribuable = 2 and port_occupation_status != 2 and card_id is not null;
    	-- INTERDIT
    	select count(port_id) from t_ports INTO _result.interdit where strp_id=_result.id and port_attribuable = 3 and port_occupation_status != 2 and card_id is not null;
        -- HS
    	select count(port_id) from t_ports INTO _result.hs where strp_id=_result.id and port_out_status in ('B','M','D') and card_id is not null;
   	
     RETURN NEXT _result;
   END LOOP;
   RETURN;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_card_national_profiles_del;
--/
CREATE FUNCTION sp_t_card_national_profiles_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	PERFORM sp_t_card_national_profiles_deleteParts(OLD.cnpr_id);
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_card_national_profiles_deleteparts;
--/
CREATE FUNCTION sp_t_card_national_profiles_deleteparts (p_cardnatprofilid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN

		DELETE FROM t_tst_on_card_nat_profiles WHERE cnpr_id = p_cardNatProfilId;
		DELETE FROM t_techno_on_card_nat_profiles WHERE	cnpr_id = p_cardNatProfilId;

	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_card_national_profiles_handledatafordtable;
--/
CREATE FUNCTION sp_t_card_national_profiles_handledatafordtable (p_cardsv_id bigint, p_newrareness smallint, p_newisadsl smallint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN

		-- Denormalisation
		UPDATE	t_d_dslam_xdsl_cards
		SET	dxcd_is_adsl = p_newIsAdsl,
			dxcd_rareness = p_newRareness
		WHERE	csfv_id = p_cardsv_id
		;
	
		-- Cas de la modification du flag dxcd_is_adsl :
		-- Levee du flag updated des chassis portant les cartes impactees faite par trigger sur dslamXdslCard

	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_card_national_profiles_upd;
--/
CREATE FUNCTION sp_t_card_national_profiles_upd ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	PERFORM sp_t_card_national_profiles_handleDataForDTable(NEW.csfv_id, NEW.cnpr_rareness, NEW.cnpr_is_adsl);
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_cards_del;
--/
CREATE FUNCTION sp_t_cards_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
--	PERFORM sp_t_cards_deleteDslamCard(OLD.card_id);
	PERFORM sp_t_cards_deleteDataFromDTable(OLD.card_id, OLD.card_runtime_type, OLD.card_nature);
	IF (OLD.slot_id IS NOT NULL) THEN
		UPDATE t_slots SET slot_occup_state = 'L' WHERE slot_id = OLD.slot_id;
	END IF;
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_cards_deletedatafromdtable;
--/
CREATE FUNCTION sp_t_cards_deletedatafromdtable (p_id bigint, pcardruntimetype character, pcardnature character)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
		--RAISE NOTICE ' -------- Debut SP sp_t_cards_deleteDataFromDTable';
        IF (pCardRuntimeType IN ('D', 'C', 'F')) THEN
                IF (pCardRuntimeType in ('D', 'F') AND pCardNature = 'X') THEN
                        DELETE FROM t_d_dslam_xdsl_cards WHERE card_id = p_id;
                END IF;
                DELETE FROM t_d_xdsl_card_stripes WHERE card_id = p_id;
        END IF;
        DELETE FROM t_tst_closed_on_cards WHERE card_id = p_id;
        --RAISE NOTICE ' -------- Debut SP sp_t_cards_deleteDataFromDTable';
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_cards_deletedslamcard;
--/
CREATE FUNCTION sp_t_cards_deletedslamcard (p_cardid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
		--RAISE NOTICE ' -------- Debut SP sp_t_cards_deleteDslamCard';
        -- La carte a toujours une configuration
        --BRASIL-440 - ini:
        --IF ((SELECT COUNT(*) FROM t_card_national_profiles cnp, t_cards c, t_card_soft_vers csv WHERE cnp.csfv_id = csv.csfv_id AND csv.csfv_id = c.csfv_id AND c.card_id = p_cardId)!=0) THEN
        IF ((SELECT COUNT(*) FROM t_card_national_profiles cnp JOIN t_card_soft_vers csv ON cnp.csfv_id = csv.csfv_id JOIN t_cards c ON csv.csfv_id = c.csfv_id WHERE c.card_id = p_cardId)!=0) THEN
        --BRASIL-440 - fin:
                PERFORM brasil_raiseException(11, '22');
        END IF;
        --RAISE NOTICE ' -------- Debut SP sp_t_cards_deleteDslamCard';
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_cards_handledatafordtable;
--/
CREATE FUNCTION sp_t_cards_handledatafordtable (p_cardid bigint, p_old_cardid bigint, p_oldsoftvers bigint, p_newsoftvers bigint, p_old_eqpt_id_delocalized bigint, p_new_eqpt_id_delocalized bigint, p_oldnodeid bigint, p_newnodeid bigint, p_newcardruntimetype character, p_newcardnature character, p_oldetatproduction character, p_newetatproduction character)  RETURNS character
  VOLATILE
AS $dbvis$
DECLARE
        w_newIsAdsl INT;
        w_newRareness INT;
        w_newUserEqId CHAR(1);
        w_nbTechFtth INT;
        w_dslamId INT;
        w_ChassisLogiqueDSLAMId INT;
	BEGIN
        w_newUserEqId = p_newCardRuntimeType;

        -- Cas d'une carte de dslam Xdsl ayant toutes les infos renseignees
        IF (p_newCardRuntimeType = 'D' AND p_new_eqpt_id_delocalized IS NOT NULL AND p_newNodeId IS NOT NULL AND p_newSoftVers IS NOT NULL AND p_newCardNature = 'X') THEN

                -- Les attributs du CNP à dénormaliser
                SELECT  cnpr_is_adsl, cnpr_rareness
                INTO    w_newIsAdsl, w_newRareness
                FROM    t_card_national_profiles
                WHERE   csfv_id = p_newSoftVers;
                
                -- Le Dslam de la carte
                -- BRASIL-440 - ini:
                --SELECT shelf.eqpt_id, shelf.shlf_id
                --INTO w_dslamId, w_ChassisLogiqueDSLAMId
                --FROM t_slots slot, t_shelfs shelf, t_cards c
                --WHERE slot.slot_id = c.slot_id --p_newSlot
                --AND c.card_id=p_cardId
                --AND slot.shlf_id = shelf.shlf_id;
                
                SELECT shelf.eqpt_id, shelf.shlf_id
  				  INTO w_dslamId, w_ChassisLogiqueDSLAMId
  				  FROM t_slots slot 
				  JOIN t_cards c ON slot.slot_id = c.slot_id
				  JOIN t_shelfs shelf ON slot.shlf_id = shelf.shlf_id
 				 WHERE c.card_id = p_cardId;
 				 --BRASIL-440 - fin:

                -- Teste si la carte est FTTH
                --BRASIL-440 - ini:
                --SELECT  COUNT(*)
                --INTO    w_nbTechFtth
                --FROM    t_techno_on_card_nat_profiles tcnp, t_technology_types t, t_card_national_profiles cnp
                --WHERE	tcnp.cnpr_id = cnp.cnpr_id
                --AND		cnp.csfv_id = p_newSoftVers
                --AND     t.tcty_id = tcnp.tcty_id
                --AND     t.tcty_name LIKE 'FTTH%';
                
 				SELECT  COUNT(*)
  				  INTO  w_nbTechFtth
				  FROM  t_techno_on_card_nat_profiles tcnp
				  JOIN  t_card_national_profiles cnp ON tcnp.cnpr_id = cnp.cnpr_id
				  JOIN  t_technology_types t ON t.tcty_id = tcnp.tcty_id
				 WHERE	cnp.csfv_id = p_newSoftVers
				   AND  t.tcty_name LIKE 'FTTH%';
				--BRASIL-440 - ini:

                IF (w_nbTechFtth != 0)
                THEN
                        w_newUserEqId = 'F';
                ELSE
                        -- La carte n'a pas encore ete inseree
                        IF (p_old_cardId IS NULL OR p_old_eqpt_id_delocalized IS NULL OR p_oldNodeId IS NULL OR p_oldSoftVers IS NULL OR p_oldEtatProduction = '') THEN

                                INSERT INTO t_d_dslam_xdsl_cards(
                                        card_id, eqpt_id, dslam_eqpt_id, shlf_id, node_id, csfv_id, dxcd_prod_status,
                                        dxcd_is_adsl, dxcd_rareness,
                                        dxcd_total_port_count, dxcd_total_used_port_count, dxcd_mnl_available_port_count, dxcd_auto_available_port_count)
                                VALUES (p_cardId, p_new_eqpt_id_delocalized, w_dslamId, w_ChassisLogiqueDSLAMId, p_newNodeId, p_newSoftVers, p_newEtatProduction,
                                        w_newIsAdsl, w_newRareness, 0, 0, 0, 0);

                        -- L'etat ou la version logicielle de la carte ont ete modifies
                        ELSIF (p_newEtatProduction IS DISTINCT FROM p_oldEtatProduction OR p_newSoftVers IS DISTINCT FROM p_oldSoftVers) THEN

                                IF (p_newSoftVers IS DISTINCT FROM p_oldSoftVers) THEN

                                        UPDATE  t_d_dslam_xdsl_cards
                                        SET     csfv_id = p_newSoftVers,
                                                dxcd_prod_status = p_newEtatProduction,
                                                dxcd_mnl_available_port_count = CASE WHEN p_newEtatProduction = 'F' THEN 0 ELSE dxcd_mnl_available_port_count END,
                                                dxcd_auto_available_port_count = CASE WHEN p_newEtatProduction = 'O' THEN dxcd_auto_available_port_count ELSE 0 END,
                                                dxcd_is_adsl = w_newIsAdsl,
                                                dxcd_rareness = w_newRareness
                                        WHERE   card_id = p_cardId;

                                        -- Levée du flag updated du chassis portant la carte si le flag isAdsl de la nouvelle softVers est différent
                                        -- de celui de l'ancienne fait par trigger sur dslamXdslCard

                                ELSE
                                        -- La version logicielle n'a pas changé
                                        UPDATE  t_d_dslam_xdsl_cards
                                        SET     dxcd_prod_status = p_newEtatProduction,
                                                dxcd_mnl_available_port_count = CASE WHEN p_newEtatProduction = 'F' THEN 0 ELSE dxcd_mnl_available_port_count END,
                                                dxcd_auto_available_port_count = CASE WHEN p_newEtatProduction = 'O' THEN dxcd_auto_available_port_count ELSE 0 END
                                        WHERE   card_id = p_cardId;

                                END IF;

                        END IF;

                END IF;

        END IF;

        RETURN w_newUserEqId;
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_cards_ins;
--/
CREATE FUNCTION sp_t_cards_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	SELECT sp_t_cards_handleDataForDTable(NEW.card_id, NULL, NULL, NEW.csfv_id, NULL, NEW.eqpt_id_delocalized, NULL, NEW.node_id, NEW.card_runtime_type, NEW.card_nature, '', NEW.card_prod_status) INTO NEW.card_runtime_type;
		-- Cas d'une carte
	    IF (NEW.card_runtime_type='D' OR NEW.card_runtime_type='F') THEN
	    	PERFORM sp_t_cards_updateCardMatrixStateInsert(NEW.card_id, NEW.card_num, NEW.slot_id);
	END IF;
	
	IF (NEW.slot_id IS NOT NULL) THEN
		UPDATE t_slots SET slot_occup_state = 'O' WHERE slot_id = NEW.slot_id;
	END IF;
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_cards_upd;
--/
CREATE FUNCTION sp_t_cards_upd ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	SELECT sp_t_cards_handleDataForDTable(NEW.card_id, OLD.card_id, OLD.csfv_id, NEW.csfv_id, OLD.eqpt_id_delocalized, NEW.eqpt_id_delocalized, OLD.node_id, NEW.node_id, NEW.card_runtime_type, NEW.card_nature, OLD.card_prod_status, NEW.card_prod_status) INTO NEW.card_runtime_type;
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_cards_upd_slot;
--/
CREATE FUNCTION sp_t_cards_upd_slot ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	IF (NEW.slot_id IS DISTINCT FROM OLD.slot_id) THEN
		IF (NEW.slot_id IS NOT NULL) THEN
			UPDATE t_slots SET slot_occup_state = 'O' WHERE slot_id = NEW.slot_id;
		END IF;
		IF (OLD.slot_id IS NOT NULL) THEN
			UPDATE t_slots SET slot_occup_state = 'L' WHERE slot_id = OLD.slot_id;
		END IF;
	END IF;	
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_cards_updatecardmatrixstateinsert;
--/
CREATE FUNCTION sp_t_cards_updatecardmatrixstateinsert (p_cardid bigint, p_cardno smallint, p_slotid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
        remarks CHAR(1);
        w_shelfId INT;
    BEGIN
	    --RAISE NOTICE ' -------- Debut SP sp_t_cards_updateCardMatrixStateInsert';
        SELECT slot.shlf_id INTO w_shelfId FROM t_slots slot WHERE slot.slot_id = p_slotId;

        select SUBSTRING(shlf_matrix FROM p_cardNo FOR 1) into remarks from t_shelfs where shlf_type='L' and shlf_id=w_shelfId;

        update t_d_dslam_xdsl_cards set dxcd_matrix=remarks where card_id=p_cardId;
        --RAISE NOTICE ' -------- Debut SP sp_t_cards_updateCardMatrixStateInsert';
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_controlable_rscs_checkminfreevcicount;
--/
CREATE FUNCTION sp_t_d_controlable_rscs_checkminfreevcicount (p_id bigint, p_newcurrthreshold integer, p_newoccupiedcount integer, p_newstocksize integer, p_newneednewvc smallint)  RETURNS smallint
  VOLATILE
AS $dbvis$
DECLARE
  w_needNewVc SMALLINT;
  MIN_FREE_VCI_COUNT INT;
BEGIN
    w_needNewVc := p_newNeedNewVc;
    MIN_FREE_VCI_COUNT := brasil_min_free_vc_count();
	IF (p_newCurrThreshold - p_newOccupiedCount < MIN_FREE_VCI_COUNT AND p_newStockSize != 0 AND p_newNeedNewVc = 0) THEN
		INSERT INTO t_d_need_new_vcs(rpct_id) VALUES(p_id);
		w_needNewVc = 1;
	END IF;
	RETURN w_needNewVc;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_controlable_rscs_checkreservation;
--/
CREATE FUNCTION sp_t_d_controlable_rscs_checkreservation (p_logicaleqa bigint, p_vpia integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
  w_nbRes INT;
BEGIN
    SELECT	COUNT(*)
	INTO	w_nbRes
	FROM	t_d_controlable_rscs
	WHERE	a_eqpt_id = p_logicalEqA
		AND	ctrs_vpia = p_vpiA
		AND	ctrs_type = 'V';

	IF (w_nbRes != 1) THEN
		--PERFORM brasil_raiseException(11, '88 '|| w_nbRes || ' - ' || p_vpiA ||' - '|| p_logicalEqA);
		PERFORM brasil_raiseException(11, '88');
	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_controlable_rscs_computenewstate;
--/
CREATE FUNCTION sp_t_d_controlable_rscs_computenewstate (p_oldstate character, p_newstate character)  RETURNS character
  VOLATILE
AS $dbvis$
DECLARE
  	w_newState CHAR(1);
BEGIN
	w_newState = p_newState;
	IF (p_newState = 'O') THEN
		IF (p_oldState = 'F') THEN
			PERFORM brasil_raiseException(11, '75');
		ELSIF (p_oldState = 'C') THEN
			PERFORM brasil_raiseException(11, '76');
		ELSIF (p_oldState = 'R') THEN
			w_newState := 'O';
		ELSIF (p_oldState = 'O') THEN
			w_newState := 'C';
		END IF;

	ELSIF (p_newState = 'F') THEN
		IF (p_oldState = 'F') THEN
			--PERFORM  brasil_raiseException(11, '77');
		ELSIF (p_oldState = 'C') THEN
			w_newState := 'O';
		END IF;

	ELSIF (p_newState = 'R') THEN
		IF (p_oldState != 'F') THEN
			PERFORM brasil_raiseException(11, '78');
		END IF;

	ELSE
		PERFORM brasil_raiseException(11, '79');
	END IF;

	RETURN w_newState;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_controlable_rscs_ins;
--/
CREATE FUNCTION sp_t_d_controlable_rscs_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	IF (NEW.rpct_id IS NULL) THEN
		PERFORM sp_t_d_controlable_rscs_checkReservation(NEW.a_eqpt_id, NEW.ctrs_vpia);
	END IF;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_controlable_rscs_upd_fulloccstate;
--/
CREATE FUNCTION sp_t_d_controlable_rscs_upd_fulloccstate ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	IF (NEW.ctrs_type = 'V' AND NEW.ctrs_role = 0) THEN
		NEW.ctrs_full_occupied_status := sp_t_d_controlable_rscs_computeNewState(OLD.ctrs_full_occupied_status, NEW.ctrs_full_occupied_status);
	END IF;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_controlable_rscs_upd_occupiedcount;
--/
CREATE FUNCTION sp_t_d_controlable_rscs_upd_occupiedcount ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	-- Cas d'un VP de collecte deja occupe au niveau VP
	IF (NEW.ctrs_type = 'V' AND NEW.ctrs_role = 0 AND NEW.ctrs_full_occupied_status != 'F' AND 1= OLD.ctrs_occupied_count) THEN
		PERFORM brasil_raiseException(11, '82');
	END IF;
	-- Cas d'un VP de collecte
	IF (NEW.ctrs_type = 'V' AND NEW.ctrs_role = 0) THEN
		NEW.ctrs_need_new_vc := sp_t_d_controlable_rscs_checkMinFreeVciCount(NEW.rpct_id, NEW.ctrs_curr_threshold, NEW.ctrs_occupied_count, NEW.ctrs_stock_size, NEW.ctrs_need_new_vc);
	END IF;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_dslam_logical_shelfs_del;
--/
CREATE FUNCTION sp_t_d_dslam_logical_shelfs_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	PERFORM sp_t_d_dslam_logical_shelfs_updateManElem(OLD.eqpt_id);
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_dslam_logical_shelfs_upd_updated;
--/
CREATE FUNCTION sp_t_d_dslam_logical_shelfs_upd_updated ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	IF (NEW.dsls_updated = 1) THEN
		PERFORM sp_t_d_dslam_logical_shelfs_updateManElem(OLD.eqpt_id);
	END IF;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_dslam_logical_shelfs_updatemanelem;
--/
CREATE FUNCTION sp_t_d_dslam_logical_shelfs_updatemanelem (p_idmanelem bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	UPDATE t_d_dslam_manelems
	SET	dsme_updated = 1
	WHERE eqpt_id = p_idManElem;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_dslam_xdsl_cards_del;
--/
CREATE FUNCTION sp_t_d_dslam_xdsl_cards_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	PERFORM sp_t_d_dslam_xdsl_cards_updateShelf(OLD.shlf_id);
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_dslam_xdsl_cards_upd;
--/
CREATE FUNCTION sp_t_d_dslam_xdsl_cards_upd ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	IF (OLD.dxcd_is_adsl != NEW.dxcd_is_adsl) THEN
		PERFORM sp_t_d_dslam_xdsl_cards_updateShelf(OLD.shlf_id);
	END IF;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_dslam_xdsl_cards_updateshelf;
--/
CREATE FUNCTION sp_t_d_dslam_xdsl_cards_updateshelf (p_idlogicalshelf bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	UPDATE	t_d_dslam_logical_shelfs
	SET	dsls_updated = 1
	WHERE shlf_id = p_idLogicalShelf;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_rsc_vcis_computenewstate;
--/
CREATE FUNCTION sp_t_d_rsc_vcis_computenewstate (p_oldstate character, p_newstate character, p_idvp bigint)  RETURNS character
  VOLATILE
AS $dbvis$
DECLARE
	w_newState CHAR(1);
BEGIN
	w_newState = p_newState;

	IF (p_newState = 'O') THEN
		IF (p_oldState = 'F') THEN
			PERFORM brasil_raiseException(11, '9');
		ELSIF (p_oldState = 'C') THEN
			PERFORM brasil_raiseException(11, '10');
		ELSIF (p_oldState = 'R') THEN
			w_newState = 'O';
		ELSIF (p_oldState = 'O') THEN
			w_newState = 'C';
		END IF;

	ELSIF (p_newState = 'F') THEN
		IF (p_oldState = 'F') THEN
			PERFORM brasil_raiseException(11, '11');
		ELSIF (p_oldState = 'C') THEN
			w_newState = 'O';
		END IF;

	ELSIF (p_newState = 'R') THEN
		IF (p_oldState != 'F') THEN
			PERFORM brasil_raiseException(11, '12');
		END IF;

	ELSE
		PERFORM brasil_raiseException(11, '13');
	END IF;


--	IF (w_newState = 'R') THEN
--		UPDATE t_d_controlable_rscs
--			SET ctrs_occupied_count = ctrs_occupied_count + 1
--			WHERE rpct_id = p_idVP;
		
--	ELSIF (w_newState = 'F') THEN
--		UPDATE t_d_controlable_rscs
--			SET ctrs_occupied_count = ctrs_occupied_count - 1
--			WHERE rpct_id = p_idVP;
--	END IF;

	RETURN w_newState;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_d_rsc_vcis_upd_state;
--/
CREATE FUNCTION sp_t_d_rsc_vcis_upd_state ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	SELECT sp_t_d_rsc_vcis_computeNewState(OLD.rscv_status, NEW.rscv_status, OLD.rpct_id) INTO NEW.rscv_status;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_distributors_del;
--/
CREATE FUNCTION sp_t_distributors_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	PERFORM sp_t_distributors_deleteRepartiteur(OLD.dist_id);
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_distributors_deleterepartiteur;
--/
CREATE FUNCTION sp_t_distributors_deleterepartiteur (p_idrep bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 
	nbTechnoExiste int;
	nbStripeExiste int;

BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_distributors_deleteRepartiteur';
	SELECT COUNT(*) FROM t_no_back_on_technos  INTO nbTechnoExiste WHERE dist_id= p_idRep;
	
	SELECT COUNT(*) FROM t_stripes INTO nbStripeExiste WHERE dist_id= p_idRep;
	
	--RAISE NOTICE '---------- nbTechnoExiste <%> isStripeExiste <%>',nbTechnoExiste,nbStripeExiste;
	-- Il a encore une configuration
	IF (nbTechnoExiste!=0 OR nbStripeExiste!=0 ) THEN
		PERFORM brasil_raiseException(11, '55');
	END IF;
	--RAISE NOTICE ' -------- FIN SP sp_t_distributors_deleteRepartiteur';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_dslam_assignments_del;
--/
CREATE FUNCTION sp_t_dslam_assignments_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	PERFORM sp_t_dslam_assignments_deleteParts(OLD.dsag_id);
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_dslam_assignments_deleteparts;
--/
CREATE FUNCTION sp_t_dslam_assignments_deleteparts (p_dslamassignmentid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	DELETE FROM t_dslam_access_constraints WHERE dsag_id = p_dslamAssignmentId;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epc_order_lines_del;
--/
CREATE FUNCTION sp_t_epc_order_lines_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
		PERFORM sp_t_epc_order_lines_deleteParts(OLD.epco_id);
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epc_order_lines_deleteparts;
--/
CREATE FUNCTION sp_t_epc_order_lines_deleteparts (p_epcorderlineid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	DELETE FROM t_tr_assignments WHERE epco_id = p_epcOrderLineId;
	DELETE FROM t_server_constraints WHERE epco_id = p_epcOrderLineId;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epc_vers_checkmrtaccesdslam;
--/
CREATE FUNCTION sp_t_epc_vers_checkmrtaccesdslam (p_idmrt integer)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	IF ((SELECT COUNT(*) FROM t_mrt_access_dslams WHERE mrtd_id = p_idMRT) = 0) THEN
		PERFORM brasil_raiseException(11, '73');
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epc_vers_del;
--/
CREATE FUNCTION sp_t_epc_vers_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	
	PERFORM sp_t_epc_vers_deleteEPCVers(OLD.epcv_id, OLD.epcv_vers_num);
			
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epc_vers_deleteepcvers;
--/
CREATE FUNCTION sp_t_epc_vers_deleteepcvers (p_idepcvers bigint, p_epcversnoversion smallint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	-- suppression des impacts
	-- REM : updateCounter pas incrémenté ici car fait dans le service irwas
	UPDATE	t_making_files
	SET		mkfl_epc_impact_size = mkfl_epc_impact_size - 1
	WHERE	mkfl_id IN (
		SELECT	mkfl_id
		FROM	t_epc_vers_impacts
		WHERE	epcv_id = p_idEPCVers
	);

	DELETE
	FROM	t_epc_vers_impacts
	WHERE	epcv_id = p_idEPCVers;

	-- Suppression des EPCVersComp
	DELETE FROM t_epc_vers_comps
	WHERE	epcv_id = p_idEPCVers
	AND	epvc_vers_num = p_EPCVersNoVersion;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epc_vers_upd_state;
--/
CREATE FUNCTION sp_t_epc_vers_upd_state ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	IF (NEW.epcv_current_state = 'E' AND OLD.epcv_current_state != 'E' AND NEW.epc_id IS NOT NULL) THEN
			 PERFORM sp_t_epc_vers_updateEpcDate(NEW.epc_id);
	END IF;
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epc_vers_updateepcdate;
--/
CREATE FUNCTION sp_t_epc_vers_updateepcdate (p_idepc bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	-- Mise a jour de la date et heure de mise en service de l'EPC
	UPDATE	t_epcs
	SET		epc_opendate_date = CURRENT_DATE,
			epc_opendate_time = cast(extract(epoch from LOCALTIME) as integer)
	WHERE	epc_id = p_idEPC
			AND (epc_opendate_date IS NULL OR epc_opendate_time IS NULL);
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epcs_checkepcprincipal;
--/
CREATE FUNCTION sp_t_epcs_checkepcprincipal (p_epcprincipal character varying)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
		IF ((SELECT COUNT(*) FROM t_epcs WHERE epc_epc_id = p_EPCPrincipal) = 0) THEN
			PERFORM brasil_raiseException(11, '72');
		END IF;
	
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epcs_del;
--/
CREATE FUNCTION sp_t_epcs_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
		PERFORM sp_t_epcs_delEPC(OLD.epc_id, OLD.epc_epc_id);
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epcs_delepc;
--/
CREATE FUNCTION sp_t_epcs_delepc (p_oldepcid bigint, p_oldepcepcid character)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nb INT;
	w_tstgroup char(1);

BEGIN
	
	select tst_group into w_tstgroup from t_tech_serv_types where tst_id in (
		select tst_id from t_tech_services where tcsv_id in (
			select tcsv_id from t_epc_vers where epc_id = p_oldEpcId 
		)
	);

	IF (w_tstgroup = 'E') THEN
	
		SELECT COUNT(*) FROM t_epcs INTO w_nb WHERE epc_main_epc_id = p_oldEpcEpcId;
		IF (w_nb != 0) THEN
			PERFORM brasil_raiseException(11, '42');
		END IF;
		
	END IF;
	
	Delete FROM t_epc_vers where epc_id = p_oldEpcId;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epcs_ins;
--/
CREATE FUNCTION sp_t_epcs_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	IF (new.epc_main_epc_id IS DISTINCT FROM '') THEN
			PERFORM sp_t_epcs_checkEPCPrincipal(NEW.epc_main_epc_id);
	END IF;
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_epcs_upd_value;
--/
CREATE FUNCTION sp_t_epcs_upd_value ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	IF (NEW.epc_main_epc_id IS DISTINCT FROM OLD.epc_main_epc_id) THEN
			PERFORM sp_t_epcs_checkEPCPrincipal(NEW.epc_main_epc_id);
	END IF;
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_equipments_checkdslamreel;
--/
CREATE FUNCTION sp_t_equipments_checkdslamreel (p_idmei integer)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN	
	
	IF ((SELECT COUNT(*) FROM T_EQUIPMENTS WHERE id = p_idMei)=0) THEN
		PERFORM brasil_raiseException(11, '26');
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_equipments_checkgestdslam;
--/
CREATE FUNCTION sp_t_equipments_checkgestdslam (p_dsmg_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_id INT;
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_equipments_checkGestDslam';
	IF (p_Dsmg_id != 0) THEN
		IF ((SELECT COUNT(*) FROM T_EQUIPMENTS WHERE eqpt_id = p_Dsmg_id)=0) THEN
			PERFORM brasil_raiseException(11, '25');
		END IF;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_equipments_checkGestDslam';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_equipments_checkmaitre;
--/
CREATE FUNCTION sp_t_equipments_checkmaitre (p_newringid brasiltype_ringtab)  RETURNS brasiltype_ringtab
  VOLATILE
AS $dbvis$
DECLARE
	w_newMaitre INT;
	w_IdMaitre INT;
	w_IdSource INT;
	w_Rank INT;
	w_newRing BrasilType_RingTab;
	nbreUpdatedLigne INT;
BEGIN	
	--RAISE NOTICE ' -------- Debut SP sp_t_equipments_checkMaitre';
	IF (p_newRingId.source IS NULL AND  p_newRingId.maitre IS NULL AND (p_newRingId.rank IS NULL OR p_newRingId.rank = 0)) THEN
		w_newRing.source := p_newRingId.source ;
		w_newRing.maitre := p_newRingId.maitre ;
		w_newRing.rank	 := p_newRingId.rank ;
	ELSE

		w_newMaitre :=  p_newRingId.maitre;

		-- Recuperation des infos du maître
		SELECT source_eqpt_id,master_eqpt_id,eqpt_rank INTO w_IdSource,w_IdMaitre,w_Rank FROM T_EQUIPMENTS WHERE EQPT_ID = w_newMaitre;
		GET DIAGNOSTICS nbreUpdatedLigne = ROW_COUNT;

		-- le dslam maître n'existe pas
		IF (nbreUpdatedLigne=0) THEN
			PERFORM brasil_raiseException(11, '28');
		END IF;

		IF (w_IdSource=0) THEN
			w_newRing.source := w_newMaitre;
			w_newRing.maitre := w_newMaitre;
			w_newRing.rank := 1;
			
		ELSE
			w_newRing.source := w_IdSource;
			w_newRing.maitre := w_newMaitre;
			w_newRing.rank := w_Rank + 1;
			
		END IF;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_equipments_checkMaitre';
	RETURN w_newRing;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_equipments_deletedatafromdtable;
--/
CREATE FUNCTION sp_t_equipments_deletedatafromdtable (p_id bigint, p_type smallint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
BEGIN	
	--RAISE NOTICE ' -------- Debut SP sp_t_equipments_deleteDataFromDTable';
	-- Cas d'un dslam ou d'un dslam delocalise
	IF (p_type = 1 OR p_type = 3) THEN
		DELETE FROM	t_d_dslam_manelems WHERE eqpt_id = p_id;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_equipments_deleteDataFromDTable';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_equipments_handledatafordtable;
--/
CREATE FUNCTION sp_t_equipments_handledatafordtable (p_id bigint, p_oldtype smallint, p_newtype smallint, p_oldusermeid integer, p_newusermeid integer, p_oldnodeid bigint, p_newnodeid bigint, p_oldconfig brasiltype_configtab, p_newconfig brasiltype_configtab, p_oldringid brasiltype_ringtab, p_newringid brasiltype_ringtab)  RETURNS brasiltype_ringtab
  VOLATILE
AS $dbvis$
DECLARE
	w_configuration BrasilType_ConfigTab;
	w_ringIdentifier BrasilType_RingTab;
	nbreUpdatedLigne INT;
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_equipments_handleDataForDTable';
	 w_ringIdentifier := p_newRingId;
	 
	--RAISE NOTICE ' -------- p_newType : %, p_newNodeId: %, p_newConfig: %, p_newRingId:%', p_newType, p_newNodeId, p_newConfig, p_newRingId;
	-- p_newType : 1, p_newNodeId: 1329625, p_newConfig: (C,O), p_newRingId:(5055322,5055322,1)
	-- Cas d'un dslam ayant toutes les infos renseignees
	
		
	IF (p_newType = 1 AND p_newNodeId != 0 AND p_newConfig IS NOT NULL AND NOT(p_newRingId IS NULL)) THEN
		--RAISE NOTICE ' -------- Condition 1 verified';
		-- Le dslam n'a pas pu etre insere avant
		IF (p_oldType = 0 OR p_oldNodeId = 0 OR p_oldConfig IS NULL OR p_oldRingId IS NULL) THEN
			--RAISE NOTICE ' -------- Condition 2 verified';
			-- Verif maitre et calcul du nouveau source
			w_ringIdentifier := sp_t_equipments_checkMaitre(p_newRingId);
			--RAISE NOTICE ' -------- Insertion dans  t_d_dslam_manelems';
			INSERT INTO t_d_dslam_manelems(
				 eqpt_id,dslam_eqpt_id, master_dslam_eqpt_id, source_dslam_eqpt_id, node_id, 
				dsme_dslam_status, dsme_prod_status, dsme_updated,
				dsme_total_port_count, dsme_total_used_port_count, dsme_mnl_available_port_count, dsme_auto_available_port_count, dsme_manelem_load)
			VALUES (p_id, p_id, w_ringIdentifier.maitre, w_ringIdentifier.source, 
			p_newNodeId, 
			p_newConfig.equiptStatus, p_newConfig.prodStatus, 0, 0, 0, 0, 0, 0);


		-- Les etats du dslam ou le maitre du dslam ont ete modifies
		ELSIF (p_newConfig.equiptStatus IS DISTINCT FROM p_oldConfig.equiptStatus OR p_newConfig.prodStatus IS DISTINCT FROM p_oldConfig.prodStatus OR p_newRingId IS DISTINCT FROM p_oldRingId) THEN

		 	-- le maitre a ete change, calcul de la nouvelle valeur du ringIdentifier
		 	IF (p_newRingId != p_oldRingId) THEN
				-- Verif et calcul du nouveau source
				w_ringIdentifier := sp_t_equipments_checkMaitre(p_newRingId);
		 	END IF;

			UPDATE	t_d_dslam_manelems
			SET	master_dslam_eqpt_id = w_ringIdentifier.maitre,
				source_dslam_eqpt_id = w_ringIdentifier.source,
				dsme_dslam_status = p_newConfig.equiptStatus,
				dsme_prod_status = p_newConfig.prodStatus,
				dsme_updated = 1,
				dsme_mnl_available_port_count = CASE WHEN p_newConfig.equiptStatus = 'R' THEN (CASE WHEN p_newConfig.prodStatus = 'F' THEN 0 ELSE dsme_mnl_available_port_count END) ELSE  0 END,
				dsme_auto_available_port_count = CASE WHEN p_newConfig.equiptStatus = 'R' THEN (CASE WHEN p_newConfig.prodStatus = 'O' THEN dsme_auto_available_port_count ELSE 0 END) ELSE 0 END
			WHERE	dslam_eqpt_id = p_id OR eqpt_id = p_id;

		END IF;

	-- Cas d'un dslam delocalise ayant toutes les infos renseignees et n'ayant pas encore ete insere
	ELSIF (p_newUserMEId != 0 AND p_newType = 3 AND p_newNodeId != 0 AND (p_oldUserMEId = 0 OR p_oldType = 0 OR p_oldNodeId = 0)) THEN

		-- Recup des infos du dslam reel
		SELECT eqpt_status, eqpt_prod_status, source_eqpt_id,master_eqpt_id
		INTO w_configuration.equiptStatus,w_configuration.prodStatus, 
			 w_ringIdentifier.source, w_ringIdentifier.maitre
		FROM t_equipments WHERE id = p_newUserMEId;
		GET DIAGNOSTICS nbreUpdatedLigne = ROW_COUNT;
		IF (nbreUpdatedLigne = 0) THEN
			PERFORM brasil_raiseException(11, '26');
		END IF;
		
		INSERT INTO t_d_dslam_manelems(
				 eqpt_id,dslam_eqpt_id, masterdslam_eqpt_id, sourcedslam_eqpt_id,
				Node_id, 
				dsme_dslam_status, dsme_prod_status, dsme_updated,
				dsme_total_port_count, dsme_total_used_port_count, dsme_mnl_available_port_count, dsme_auto_available_port_count, dsme_manelem_load)
			VALUES (p_id, p_newUserMEId, w_ringIdentifier.maitre, w_ringIdentifier.source, 
			p_newNodeId, 
			w_configuration.equiptStatus, w_configuration.prodStatus, 0, 0, 0, 0, 0, 0);

	END IF;

	--RAISE NOTICE ' -------- Fin SP sp_t_equipments_handleDataForDTable';
	RETURN w_ringIdentifier; 
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_equipments_updatedataforresourcedtable;
--/
CREATE FUNCTION sp_t_equipments_updatedataforresourcedtable (p_id bigint, p_newsaturatednip character)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN	
	--RAISE NOTICE ' -------- Debut SP sp_t_equipments_updateDataForResourceDTable';
	UPDATE t_d_rsc_dslam_tsfs SET rscd_saturated_nip = p_newSaturatedNip WHERE nip_eqpt_id = p_id;
	--RAISE NOTICE ' -------- Fin SP sp_t_equipments_updateDataForResourceDTable';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_making_files_del;
--/
CREATE FUNCTION sp_t_making_files_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	PERFORM sp_t_making_files_deleteParts(OLD.mkfl_id);
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_making_files_deleteparts;
--/
CREATE FUNCTION sp_t_making_files_deleteparts (p_makingfileid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	DELETE FROM t_dslam_assignments WHERE mkfl_id = p_makingFileId;
	DELETE FROM t_epc_order_lines WHERE	mkfl_id = p_makingFileId;
	DELETE FROM t_epc_vers_impacts WHERE mkfl_id = p_makingFileId;
	DELETE FROM t_mrt_vers_impacts WHERE mkfl_id = p_makingFileId;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_checkuniqlientrans;
--/
CREATE FUNCTION sp_t_media_links_checkuniqlientrans (p_newfunctioncode bigint, p_newintserialno character, p_newfarenda bigint, p_newfarendb bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_maxIntSerialNo INT;

	w_nbQuad INT;
	w_nbQuadInv INT;

BEGIN
	SELECT	fctc_type
	INTO	w_maxIntSerialNo
	FROM	t_function_codes
	WHERE	fctc_id = p_newFunctionCode;

	--RAISE NOTICE '---------------------------- w_maxIntSerialNo = <%>',w_maxIntSerialNo;
	-- On ne fait le controle que s'il s'agit d'un lien de trans <-> maxIntSerialNo = 4
	IF (w_maxIntSerialNo = 4) THEN

			
		SELECT	COUNT(*)
		INTO	w_nbQuad
		FROM	t_media_links
		WHERE	mdlk_serial_num = p_newIntSerialNo
			AND	fctc_id = p_newFunctionCode
			AND	a_node_id = p_newFarEndA
			AND	b_node_id = p_newFarEndB;

		IF (p_newFarEndA != p_newFarEndB) THEN
			SELECT	COUNT(*)
			INTO	w_nbQuadInv
			FROM	t_media_links
			WHERE	mdlk_serial_num = p_newIntSerialNo
				AND	fctc_id = p_newFunctionCode
				AND	a_node_id = p_newFarEndB
				AND	b_node_id = p_newFarEndA
			;
		ELSE
			w_nbQuadInv := 0;
		END IF;

		--RAISE NOTICE '--------------- w_nbQuad = <%>, w_nbQuadInv = <%>',w_nbQuad, w_nbQuadInv;
		IF ((w_nbQuad + w_nbQuadInv) != 0 ) THEN
			PERFORM brasil_raiseException(11, '87');
		END IF;


	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_del;
--/
CREATE FUNCTION sp_t_media_links_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	-- Cas d'un lien support
	PERFORM sp_t_media_links_delLS(old.a_port_id, old.b_port_id, old.mdlk_point_b_phys_end_type);
		
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_dells;
--/
CREATE FUNCTION sp_t_media_links_dells (p_porta_id bigint, p_portb_id bigint, p_typeextrphy_b character)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	-- ExtB = ExtPort
	IF (p_typeExtrPhy_b='P') THEN

		UPDATE t_ports SET port_occup_ont=port_occup_ont-1 WHERE port_id=p_portA_id OR port_id=p_portB_id;

	-- ExtB = ExtPortNPA ou ExtClient -> rien a faire
	ELSE

		UPDATE t_ports SET port_occup_ont=port_occup_ont-1 WHERE port_id=p_portA_id;

	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_ins;
--/
CREATE FUNCTION sp_t_media_links_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	oldAddInfoA BrasilType_AddInfo;
	newAddInfoA BrasilType_AddInfo;
	--listeAddInfo BrasilType_AddInfo[2];

	oldAddInfoB BrasilType_AddInfo;
	newAddInfoB BrasilType_AddInfo;
BEGIN
	
	-- FSC T-142 : horodatage de tables en BDD Brasil
	NEW.mdlk_creation_time = clock_timestamp(); 
	
	newAddInfoA.port_id := new.a_port_id;
	newAddInfoA.typeExtPhys := new.mdlk_point_a_phys_end_type;
	--newAddInfoA.typeInterface := new.mdlk_point_a_interface_type;
	--newAddInfoA.interfaceId := new.mdlk_point_a_interface_id;
	
	
	newAddInfoB.port_id := new.b_port_id;
	newAddInfoB.ce_eqpt_id := new.ce_eqpt_id;
	newAddInfoB.typeExtPhys := new.mdlk_point_b_phys_end_type;
	--newAddInfoB.typeInterface := new.mdlk_point_b_interface_type;
	--newAddInfoB.interfaceId := new.mdlk_point_b_interface_id;
	newAddInfoB.ce_eqpt_id := new.ce_eqpt_id;
	newAddInfoB.ce_shelf_num := new.mdlk_point_b_ce_shelf_num;
	newAddInfoB.ce_card_num := new.mdlk_point_b_ce_card_num;
	newAddInfoB.ce_port_num := new.mdlk_point_b_ce_port_num;
	newAddInfoB.mdlk_point_b_cust_eqpt_info := new.mdlk_point_b_cust_eqpt_info;


	PERFORM sp_t_media_links_ptsExtLS(oldAddInfoA, newAddInfoA, oldAddInfoB, newAddInfoB);
	--listeAddInfo := f_t_media_links_ptsExtLS(old.oldAddInfoA, new.newAddInfoA, old.oldAddInfoB, new.newAddInfoB);
			
	-- Gestion equipements extremites
	/*IF (new.a_eqpt_id!="" AND new.b_eqpt_id!="") THEN
		sp_checkEqs(new.a_eqpt_id, new.b_eqpt_id);
	END IF;*/
	
	
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_mutation;
--/
CREATE FUNCTION sp_t_media_links_mutation ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE

	w_oldExtA BrasilType_AddInfo;
	w_oldExtB BrasilType_AddInfo;
	
	w_idOldEqA BIGINT;
	w_idOldEqB BIGINT;
	w_idTC BIGINT;
BEGIN
	
	w_oldExtA.port_id =  old.a_port_id;
	w_oldExtA.typeExtPhys =  old.mdlk_point_a_phys_end_type;
	w_oldExtB.port_id =  old.b_port_id;
	w_oldExtB.typeExtPhys = old.mdlk_point_b_phys_end_type;
	w_oldExtB.ce_eqpt_id = old.ce_eqpt_id;
	w_oldExtB.ce_shelf_num = old.mdlk_point_b_ce_shelf_num;
	w_oldExtB.ce_card_num = old.mdlk_point_b_ce_card_num;
	w_oldExtB.ce_port_num = old.mdlk_point_b_ce_port_num;
	w_oldExtB.mdlk_point_b_cust_eqpt_info = old.mdlk_point_b_cust_eqpt_info;
	w_idOldEqA = old.a_eqpt_id;
	w_idOldEqB = old.b_eqpt_id;
	w_idTC = old.mdlk_id;
	
	IF (NOT(new.mdlk_migration_infos IS NULL) AND SUBSTRING(new.mdlk_migration_infos FROM 1 FOR 2) = 'ML') THEN
		PERFORM sp_t_media_links_mutationLS(old.mdlk_id, new.mdlk_id, old.mdlk_migration_infos, new.mdlk_migration_infos,w_oldExtA,w_oldExtB,w_idOldEqA,w_idOldEqB,w_idTC);
		new.mdlk_migration_infos := '';
	END IF;
	
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_mutationls;
--/
CREATE FUNCTION sp_t_media_links_mutationls (p_old_mdlk_id bigint, p_new_mdlk_id bigint, p_oldvorgang character, p_newvorgang character, w_oldexta brasiltype_addinfo, w_oldextb brasiltype_addinfo, w_idoldeqa bigint, w_idoldeqb bigint, w_idtc bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	-- Les elements qui peuvent etre modifie
	w_idNewEqA		INT;
	w_idNewNodeA		INT;
	w_newExtA		BrasilType_AddInfo;
	w_idNewEqB		INT;
	w_idNewNodeB		INT;
	w_newExtB		BrasilType_AddInfo;

	w_idNewNodeCA		INT;
	w_idNewNodeCB		INT;

	w_oldExtGrpeA		BrasilType_AddInfo;
	w_newExtGrpeA		BrasilType_AddInfo;
	w_oldExtGrpeB		BrasilType_AddInfo;
	w_newExtGrpeB		BrasilType_AddInfo;
	w_ExtGrpeA		BrasilType_AddInfo[];
	w_ExtGrpeB		BrasilType_AddInfo[];

	w_casLienSurGroupe	INT;

	-- nb utilisateur ExtB
	w_nbUtilNewB		INT;
	w_nbUtilNewB1		INT;

	-- Pour comparaison en utilisant l'index
	w_extAPortComp		BrasilType_AddInfo;
	w_extBPortComp		BrasilType_AddInfo;
	w_extBNPAComp		BrasilType_AddInfo;
	
	w_typeExtPhysB CHAR(1);
BEGIN
	-- les TCVers qui ont le oldExtA en extremite A (pas d'interface id)
	CREATE TEMP TABLE TCVersPtAEndA(
		rpct_id BIGINT
	);--$TABLE_STORAGE_CLAUSE;

	-- les TCVers qui ont le oldExtA en extremite B (pas d'interface id)
	CREATE TEMP TABLE TCVersPtAEndB(
		rpct_id BIGINT
	);--$TABLE_STORAGE_CLAUSE;

	-- les TCVers qui ont le oldExtB en extremite A
	CREATE TEMP TABLE TCVersPtBEndA(
		rpct_id BIGINT
	);--$TABLE_STORAGE_CLAUSE;

	-- les TCVers qui ont le oldExtB en extremite B
	CREATE TEMP TABLE TCVersPtBEndB(
		rpct_id BIGINT
	);--$TABLE_STORAGE_CLAUSE;

	CREATE TEMP TABLE GroupedPCP(
		pcp_id		INT,
		usageCounter INT, -- compteur d'occupation
		logUsageCounter	smallint,	-- compteur d'occupation logique
		position	INT,		-- position du port dans le groupe (POA croissant)
		endAB		INT,		-- 0 si en A, 1 si en B
		isSource	INT		-- 1 si PCP du groupe source, 0 sinon
	);--$TABLE_STORAGE_CLAUSE;

	-- les TC des groupes
	CREATE TEMP TABLE GroupedTC(
		mdlk_id		INT,
		old_pcp_id	BIGINT,	-- ancien port
		new_pcp_id	BIGINT,	-- nouveau port
		endAB		INT	-- extrémité impactée, 0 si A, 1 si B
	);--$TABLE_STORAGE_CLAUSE;


	IF (p_old_mdlk_id = 0 OR p_oldVorgang = '' OR p_oldVorgang IS NULL) THEN

		IF (p_new_mdlk_id != 0 AND p_newVorgang IS DISTINCT FROM '' AND p_newVorgang IS NOT NULL) THEN


			--LET w_idNewEqA = DECODE(p_newVorgang[4], ' ', 0, p_newVorgang[4,11]::INT);
			w_idNewEqA := CASE WHEN trim(FROM SUBSTRING(p_newVorgang FROM 4 FOR 1))  = '' THEN 0 ELSE SUBSTRING(p_newVorgang FROM 4 FOR 8)::INT END;
			--LET w_idNewNodeA = DECODE(p_newVorgang[13], ' ', 0, p_newVorgang[13,22]::INT);
			w_idNewNodeA := CASE WHEN trim(FROM SUBSTRING(p_newVorgang FROM 13 FOR 1)) = '' THEN 0 ELSE SUBSTRING(p_newVorgang FROM 13 FOR 10)::INT END;
			
			--w_newExtA := p_newVorgang[24,41];
			IF(trim(FROM SUBSTRING(p_newVorgang FROM 24 FOR 1)) != '') THEN
				w_newExtA.port_id := SUBSTRING(p_newVorgang FROM 24 FOR 9)::INT;
				w_newExtA.typeExtPhys := SUBSTRING(p_newVorgang FROM 33 FOR 1);
				w_newExtA.typeInterface := SUBSTRING(p_newVorgang FROM 37 FOR 1);
				--w_newExtA.interfaceId := SUBSTRING(p_newVorgang FROM 38 FOR 4);
			END IF;
			
			--LET w_idNewEqB = DECODE(p_newVorgang[43], ' ', 0, p_newVorgang[43,50]::INT);
			w_idNewEqB := CASE WHEN trim(FROM SUBSTRING(p_newVorgang FROM 43 FOR 1)) = '' THEN 0 ELSE SUBSTRING(p_newVorgang FROM 43 FOR 8)::INT END;
			--LET w_idNewNodeB = DECODE(p_newVorgang[52], ' ', 0, p_newVorgang[52,61]::INT);
			w_idNewNodeB := CASE WHEN trim(FROM SUBSTRING(p_newVorgang FROM 52 FOR 1)) = '' THEN 0 ELSE SUBSTRING(p_newVorgang FROM 52 FOR 10)::INT END;
			--w_newExtB := p_newVorgang[63,80];

			IF(trim(FROM SUBSTRING(p_newVorgang FROM 63 FOR 1)) != '') THEN
				w_typeExtPhysB := SUBSTRING(p_newVorgang FROM 72 FOR 1);
				IF (w_typeExtPhysB = 'P') THEN
					w_newExtB.port_id := SUBSTRING(p_newVorgang FROM 63 FOR 9)::INT;
					w_newExtB.typeExtPhys := SUBSTRING(p_newVorgang FROM 72 FOR 1);
					w_newExtB.typeInterface := SUBSTRING(p_newVorgang FROM 76 FOR 1);
					--w_newExtB.interfaceId := SUBSTRING(p_newVorgang FROM 77 FOR 4);
				ELSIF ( w_typeExtPhysB = 'N') THEN
					w_newExtB.ce_eqpt_id := SUBSTRING(p_newVorgang FROM 63 FOR 8)::INT;
					w_newExtB.typeExtPhys := SUBSTRING(p_newVorgang FROM 72 FOR 1);
					w_newExtB.ce_shelf_num := SUBSTRING(p_newVorgang FROM 73 FOR 2)::SMALLINT;
					w_newExtB.ce_card_num := SUBSTRING(p_newVorgang FROM 75 FOR 2)::SMALLINT;
					w_newExtB.ce_port_num := SUBSTRING(p_newVorgang FROM 77 FOR 3)::SMALLINT;
					w_newExtB.typeInterface := SUBSTRING(p_newVorgang FROM 80 FOR 1);
					
				ELSIF ( w_typeExtPhysB = 'E') THEN
					w_newExtB.mdlk_point_b_cust_eqpt_info := SUBSTRING(p_newVorgang FROM 63 FOR 8);
					w_newExtB.typeExtPhys := SUBSTRING(p_newVorgang FROM 72 FOR 1);
					w_newExtB.typeInterface := SUBSTRING(p_newVorgang FROM 73 FOR 1);
				END IF;
			END IF;
			
			-- Par defaut, on met les nodeC a 0
			w_idNewNodeCA := 0;
			w_idNewNodeCB := 0;

			-- Par défaut, on dit qu'on est sur un cas de lien sur port isolé ou port NPA.
			w_casLienSurGroupe := 0;

			-- Si les 2 sont modifies, et qu'ils sont egaux, on leve une exception
			IF (NOT(w_newExtA IS NULL) AND w_newExtA IS NOT DISTINCT FROM w_newExtB) THEN
				PERFORM brasil_raiseException(11, '83');
			END IF;		

			-- Au cas ou Ironman ferait un insert/update
			IF ((NOT(w_newExtA IS NULL) AND w_oldExtA != w_newExtA) OR (NOT(w_newExtB IS NULL) AND w_oldExtB != w_newExtB)) THEN


				-- -------------------------------------------------------------------------------------------------------
				-- Détection des impacts de la mutation sur les liens trans, supportés et port / groupes
				-- -------------------------------------------------------------------------------------------------------

				-- L'extA a ete modifiee
				IF (NOT(w_newExtA IS NULL)) THEN

					--LET w_idNewNodeCA = brasil_ExternContPers_getNodeC(w_idNewNodeA);
					--w_idNewNodeCA := w_idNewNodeA;

					-- REM : côté A, le lien trans ne peut être affecté que sur un port (ExtPort)
					-- qui est soit isolé, soit dans un groupe réel, soit dans un groupe liste.
					-- L'appel ci-après est chargé traiter ces différents cas de figure.


					-- Verifie les contraintes sur les extrémités.
					-- Si oldExtA est un port isolé, le retourne inchangé pour continuer le traitement pré-existant
					-- Si oldExtA est un port dans un groupe reel, retourne les groupes associés aux ports source et cible
					-- Si oldExtA est un port dans un groupe liste, exception
					w_ExtGrpeA := f_t_media_links_checkTranslateExtAndUpdatePointForMutLS(w_oldExtA.port_id, w_newExtA.port_id, 0);
					w_oldExtGrpeA := w_ExtGrpeA[0]; 
					w_newExtGrpeA := w_ExtGrpeA[1];

					-- Si le lien est sur un port isolé
					IF (w_oldExtGrpeA.typeExtPhys = 'P') THEN

						w_extAPortComp := w_oldExtA;

						-- Mise a jour et verif des contraintes sur port cible et port source
						PERFORM sp_t_media_links_updatePoint(w_oldExtA.port_id, w_newExtA.port_id);

					-- le lien est sur un port groupé
					ELSE
						-- Cas de figure
						w_casLienSurGroupe := 1;
						-- Pour détecter les ressources logiques sur le groupe
						w_extAPortComp := w_oldExtGrpeA;
						-- Pour compatibilité avec les traitements pré-existants qui sont conservés (mutation sur port isolé)
						w_newExtA := w_newExtGrpeA;
					END IF;

					-- Remplissage des tables contenant les TCVers se terminant sur l'extremite A en A et en B
					-- On recupere uniquement: les VP, les VLAN et SrIP
					INSERT INTO TCVersPtAEndA(rpct_id)
					SELECT	rpct_id
					FROM	t_res_prod_controlables
					WHERE	((w_extAPortComp.typeExtPhys = 'P' AND w_extAPortComp.port_id=a_port_id) OR (w_extAPortComp.typeExtPhys = 'G' AND w_extAPortComp.pogr_id=a_pogr_id))
					AND	rpct_type IN ('V', 'W', 'I');

					INSERT INTO TCVersPtAEndB(rpct_id)
					SELECT	rpct_id
					FROM	t_res_prod_controlables
					WHERE	((w_extAPortComp.typeExtPhys = 'P' AND w_extAPortComp.port_id=b_port_id) OR (w_extAPortComp.typeExtPhys = 'G' AND w_extAPortComp.pogr_id=b_pogr_id))
					AND	rpct_type = 'V';
					/*INSERT INTO TCVersPtAEndA(idTCVers, idTC)
					SELECT	id,
						X1077_43_respondMO
					FROM	TCVers
					WHERE	X1588_102_mychars LIKE w_extAPortComp
					AND	X1588_52_mychars IN ('V', 'W', 'I');

					INSERT INTO TCVersPtAEndB(idTCVers, idTC)
					SELECT	id,
						X1077_43_respondMO
					FROM	TCVers
					WHERE	X1588_55_mychars LIKE w_extAPortComp
					AND	X1588_52_mychars = 'V';*/

				END IF;

				-- L'extB a ete modifiee
				IF (NOT(w_newExtB IS NULL)) THEN

					--LET w_idNewNodeCB = brasil_ExternContPers_getNodeC(w_idNewNodeB);
					--w_idNewNodeCB := w_idNewNodeB;

					-- REM : côté B, le lien trans ne peut être affecté que sur un port (ExtPort)
					-- qui est soit isolé, soit dans un groupe réel, soit dans un groupe liste, sur un port NPA

					-- On commence par traiter le cas port NPA
					IF (w_newExtB.typeExtPhys = 'N') THEN

						-- le nouveau port ne doit pas etre occupe
						SELECT COUNT(*) FROM t_media_links INTO	w_nbUtilNewB1
						WHERE ce_eqpt_id = w_newExtB.ce_eqpt_id AND  mdlk_point_b_ce_shelf_num = w_newExtB.ce_shelf_num
						AND mdlk_point_b_ce_card_num = w_newExtB.ce_card_num AND mdlk_point_b_ce_port_num = w_newExtB.ce_port_num
						AND mdlk_point_b_phys_end_type = 'N';
						
						SELECT COUNT(*) FROM t_res_prod_controlables INTO w_nbUtilNewB
						WHERE ce_eqpt_id = w_newExtB.ce_eqpt_id AND  rpct_point_b_ce_shelf_num = w_newExtB.ce_shelf_num
						AND rpct_point_b_ce_card_num = w_newExtB.ce_card_num AND rpct_point_b_ce_port_num = w_newExtB.ce_port_num
						AND rpct_point_b_phys_end_type = 'N' AND rpct_type = 'V';

						
						--LET w_extBNPAComp = w_newExtB[1,17] || "%";
						/*SELECT 	COUNT(*)
						INTO	w_nbUtilNewB
						FROM	TCVers
						WHERE	X1588_55_mychars LIKE w_extBNPAComp;*/

						IF (w_nbUtilNewB + w_nbUtilNewB1 != 1) THEN
							PERFORM brasil_raiseException(11, '64');
						END IF;


						-- Remplissage des tables contenant les TCVers se terminant sur l'extremite B en B
						-- Un port de NPA ne peut etre qu'en B et ne peut être occupé que par un VP

						--LET w_extBNPAComp = w_oldExtB[1,17] || "%";

						INSERT INTO TCVersPtBEndB(rpct_id)
						SELECT rpct_id FROM t_res_prod_controlables
						WHERE ce_eqpt_id = w_oldExtB.ce_eqpt_id AND  rpct_point_b_ce_shelf_num = w_oldExtB.ce_shelf_num
						AND rpct_point_b_ce_card_num = w_oldExtB.ce_card_num AND rpct_point_b_ce_port_num = w_oldExtB.ce_port_num
						AND rpct_point_b_phys_end_type = 'N' AND rpct_type = 'V';
						
						/*
						INSERT INTO TCVersPtBEndB(idTCVers, idTC)
						SELECT	id,
							X1077_43_respondMO
						FROM	TCVers
						WHERE	X1588_55_mychars LIKE w_extBNPAComp
						AND	X1588_52_mychars = 'V'
						;*/

					-- Dans le cas port isolé / port groupé, l'appel ci-après est chargé traiter ces différents cas de figure.
					ELSE
						-- Verifie les contraintes sur les extrémités.
						-- Si oldExtB est un port isolé, le retourne inchangé pour continuer le traitement pré-existant
						-- Si oldExtB est un port dans un groupe reel, retourne les groupes associés aux ports source et cible
						-- Si oldExtB est un port dans un groupe liste, exception
						w_ExtGrpeB := f_t_media_links_checkTranslateExtAndUpdatePointForMutLS(w_oldExtB.port_id, w_newExtB.port_id, 1);
						w_oldExtGrpeB := w_ExtGrpeB[0]; 
						w_newExtGrpeB := w_ExtGrpeB[1];


						-- Si le lien est sur un port isolé
						IF (w_oldExtGrpeB.typeExtPhys = 'P') THEN

							w_extBPortComp := w_oldExtB;

							-- Mise a jour et verif des contraintes sur port cible et port source
							PERFORM sp_t_media_links_updatePoint(w_oldExtB.port_id, w_newExtB.port_id);

						-- le lien est sur un port groupé
						ELSE
							-- Cas de figure
							w_casLienSurGroupe := 1;
							-- Pour détecter les ressources logiques sur le groupe
							w_extBPortComp := w_oldExtGrpeB;
							-- Pour compatibilité avec les traitements conservés (mutation sur port isolé)
							w_newExtB := w_newExtGrpeB;
						END IF;

						-- Remplissage des tables contenant les TCVers se terminant sur l'extremite B en A et en B
						-- On recupere uniquement: les VP, les VLAN et SrIP
						INSERT INTO TCVersPtBEndA(rpct_id)
						SELECT	rpct_id
						FROM	t_res_prod_controlables
						WHERE	((w_extBPortComp.typeExtPhys = 'P' AND w_extBPortComp.port_id=a_port_id) OR (w_extBPortComp.typeExtPhys = 'G' AND w_extBPortComp.pogr_id=a_pogr_id))
						AND	rpct_type IN ('V', 'W', 'I');
	
						INSERT INTO TCVersPtBEndB(rpct_id)
						SELECT	rpct_id
						FROM	t_res_prod_controlables
						WHERE	((w_extBPortComp.typeExtPhys = 'P' AND w_extBPortComp.port_id=b_port_id) OR (w_extBPortComp.typeExtPhys = 'G' AND w_extBPortComp.pogr_id=b_pogr_id))
						AND	rpct_type = 'V';
						
						/*INSERT INTO TCVersPtBEndA(idTCVers, idTC)
						SELECT	id,
							X1077_43_respondMO
						FROM	TCVers
						WHERE	X1588_102_mychars LIKE w_extBPortComp
						AND	X1588_52_mychars IN ('V', 'W', 'I')
						;

						INSERT INTO TCVersPtBEndB(idTCVers, idTC)
						SELECT	id,
							X1077_43_respondMO
						FROM	TCVers
						WHERE	X1588_55_mychars LIKE w_extBPortComp
						AND	X1588_52_mychars = 'V'
						;*/

					END IF;
				END IF;

			
				-- -------------------------------------------------------------------------------------------------------
				-- Mise a jour du (des) Lien(s) Support(s)
				-- Ici, on distingue les cas lien sur port isolé / lien sur port groupé.
				-- -------------------------------------------------------------------------------------------------------

				-- Traitement port isolé / port NPA
				IF w_casLienSurGroupe = 0 THEN

					-- On ne modifie la TC que si un des 2 noeuds a change
					-- classId a -1 pour que le trigger laisse passer la modif
					/*IF (w_idNewNodeA != 0 OR w_idNewNodeB != 0) THEN
						
						UPDATE	TC
						SET		X1563_1_cmNode = DECODE(w_idNewNodeA, 0, X1563_1_cmNode, w_idNewNodeA),
								X1563_3_cmNode = DECODE(w_idNewNodeB, 0, X1563_3_cmNode, w_idNewNodeB),
								classId = -1
						WHERE 	id = w_idTC
						;
					END IF;*/

					-- Dans tous les cas, on modifie la TCVers
					-- X1588_87_cmFarEndA = -1 pour que le trigger laisse passer la modif concernant les nodeC
					-- X1588_93_cmPath = -1 pour que le trigger laisse passer la modif des equipement extremite
					-- classId = -1 pour que le trigger laisse passer la modif des extremites
					UPDATE t_media_links SET 
						a_node_id = CASE WHEN w_idNewNodeA = 0 THEN a_node_id ELSE w_idNewNodeA END,
						b_node_id = CASE WHEN w_idNewNodeB = 0 THEN b_node_id ELSE w_idNewNodeB END,
						a_eqpt_id = CASE WHEN w_idNewEqA = 0 THEN a_eqpt_id ELSE w_idNewEqA END,
						b_eqpt_id = CASE WHEN w_idNewEqB = 0 THEN b_eqpt_id ELSE w_idNewEqB END,
						mdlk_point_a_phys_end_type = CASE WHEN w_newExtA IS NULL THEN mdlk_point_a_phys_end_type ELSE w_newExtA.typeExtPhys END,
						a_port_id = CASE WHEN w_newExtA IS NULL THEN a_port_id ELSE w_newExtA.port_id END
						WHERE mdlk_id = w_idTC;
						
					IF (NOT(w_newExtB IS NULL)) THEN
						IF(w_newExtB.typeExtPhys = 'P') THEN
							UPDATE t_media_links SET 
							mdlk_point_b_phys_end_type =  w_newExtB.typeExtPhys, b_port_id = w_newExtB.port_id
							WHERE mdlk_id = w_idTC;
						ELSIF (w_newExtB.typeExtPhys = 'N') THEN
							UPDATE t_media_links SET 
							mdlk_point_b_phys_end_type =  w_newExtB.typeExtPhys, ce_eqpt_id = w_newExtB.ce_eqpt_id, 
							mdlk_point_b_ce_shelf_num = w_newExtB.ce_shelf_num, 
							mdlk_point_b_ce_card_num = w_newExtB.ce_card_num, 
							mdlk_point_b_ce_port_num = w_newExtB.ce_port_num
							WHERE mdlk_id = w_idTC;
						END IF;
					END IF;
					/*UPDATE	TCVers
					SET		X1588_88_cmFarEndA = DECODE(w_idNewNodeCA, 0, X1588_88_cmFarEndA, w_idNewNodeCA),
							X1588_90_cmFarEndB = DECODE(w_idNewNodeCB, 0, X1588_90_cmFarEndB, w_idNewNodeCB),
							X1588_87_cmFarEndA = -1,
							X1588_69_mychars = DECODE(w_idNewEqA, 0, X1588_69_mychars, RPAD(w_idNewEqA, 13, ' ')),
							X1588_70_mychars = DECODE(w_idNewEqB, 0, X1588_70_mychars, RPAD(w_idNewEqB, 13, ' ')),
							X1588_93_cmPath = DECODE(w_idNewEqA, 0, DECODE(w_idNewEqB, 0, X1588_93_cmPath, -1), -1),
							X1588_102_mychars = DECODE(w_newExtA[1], ' ', X1588_102_mychars, RPAD(w_newExtA, 96, ' ')),
							X1588_55_mychars = DECODE(w_newExtB[1], ' ', X1588_55_mychars, RPAD(w_newExtB, 20, ' ')),
							classId = -1
					WHERE	id = w_idTCVers
					;*/

				-- Lien sur groupe
				ELSE
					-- 1. On récupère toutes les TC / TCVers lien support du groupe source
					--BRASIL-440 - ini:
					--INSERT
					--INTO	GroupedTC
					--SELECT	--{+ ORDERED}
					--	mdlk.mdlk_id,
					--	gpo.pcp_id,
					--	gpn.pcp_id,
					--	gpo.endAB
					--FROM	GroupedPCP gpo,
					--	GroupedPCP gpn,
					--	t_media_links mdlk
					--WHERE	gpo.isSource = 1
					--AND	gpo.endAB = 0	-- à l'origine
					--AND	gpn.isSource = 0
					--AND	gpn.position = gpo.position
					--AND	gpn.endAB = gpo.endAB
					--AND	mdlk.a_port_id = gpo.pcp_id
					--AND mdlk.mdlk_point_a_phys_end_type = 'P';
					INSERT
					  INTO GroupedTC 
					SELECT --{+ ORDERED}
					  	   mdlk.mdlk_id,
					  	   gpo.pcp_id,
					  	   gpn.pcp_id,
					  	   gpo.endAB
					  FROM GroupedPCP gpo 
					  JOIN GroupedPCP gpn ON (gpn.position = gpo.position AND gpn.endAB = gpo.endAB)
					  JOIN t_media_links mdlk ON (mdlk.a_port_id = gpo.pcp_id)
					 WHERE gpo.isSource = 1
					   AND gpo.endAB = 0	-- à l'origine
					   AND gpn.isSource = 0    
					   AND mdlk.mdlk_point_a_phys_end_type = 'P';
					--BRASIL-440 - fin:
					
					   
					   
					--BRASIL-440 - ini:
					--INSERT
					--INTO	GroupedTC
					--SELECT	--{+ ORDERED}
					--	mdlk.mdlk_id,
					--	gpo.pcp_id,
					--	gpn.pcp_id,
					--	gpo.endAB
					--FROM	GroupedPCP gpo,
					--	GroupedPCP gpn,
					--	t_media_links mdlk
					--WHERE	gpo.isSource = 1
					--AND	gpo.endAB = 1	-- à l'extrémité
					--AND	gpn.isSource = 0
					--AND	gpn.position = gpo.position
					--AND	gpn.endAB = gpo.endAB
					--AND	mdlk.b_port_id = gpo.pcp_id
					--AND mdlk.mdlk_point_b_phys_end_type = 'P';
					
					INSERT
					  INTO GroupedTC
					SELECT --{+ ORDERED}
					       mdlk.mdlk_id,
					  	   gpo.pcp_id,
					  	   gpn.pcp_id,
					  	   gpo.endAB
					  FROM GroupedPCP gpo
					  JOIN GroupedPCP gpn ON (gpn.position = gpo.position AND gpn.endAB = gpo.endAB)
					  JOIN t_media_links mdlk ON mdlk.b_port_id = gpo.pcp_id
					 WHERE gpo.isSource = 1
					   AND gpo.endAB = 1	-- à l'extrémité
					   AND gpn.isSource = 0
					   AND mdlk.mdlk_point_b_phys_end_type = 'P';
					--BRASIL-440 - fin:

					-- 2. Mise à jour des TC si un des deux noeuds a changé

					/*IF (w_idNewNodeA != 0 OR w_idNewNodeB != 0) THEN
						UPDATE	TC
						SET	X1563_1_cmNode = DECODE(w_idNewNodeA, 0, X1563_1_cmNode, w_idNewNodeA),
							X1563_3_cmNode = DECODE(w_idNewNodeB, 0, X1563_3_cmNode, w_idNewNodeB),
							classId = -1
						WHERE 	id IN (
							SELECT	DISTINCT tc_id	-- car une TC peut apparaitre deux fois (en A et en B)
							FROM	GroupedTC
						);
					END IF;*/

					-- 3. Dans tous les cas, on modifie la TCVers

					-- X1588_87_cmFarEndA = -1 pour que le trigger laisse passer la modif concernant les nodeC
					-- X1588_93_cmPath = -1 pour que le trigger laisse passer la modif des equipement extremite
					-- classId = -1 pour que le trigger laisse passer la modif des extremites

					-- TCvers impactées à l'origine
					UPDATE t_media_links mdlk SET 
					a_node_id = CASE WHEN w_idNewNodeA = 0 THEN a_node_id ELSE w_idNewNodeA END,
					a_eqpt_id = CASE WHEN w_idNewEqA = 0 THEN a_eqpt_id ELSE w_idNewEqA END,
					mdlk_point_a_phys_end_type = 'P',
					a_port_id = gt.new_pcp_id
					FROM	GroupedTC gt
					WHERE	gt.mdlk_id = mdlk.mdlk_id
					AND	gt.endAB = 0;
						
						
					/*	
					UPDATE	TCVers
					SET	(X1588_88_cmFarEndA,
						 X1588_87_cmFarEndA,
						 X1588_69_mychars,
						 X1588_93_cmPath,
						 X1588_102_mychars,
						 classId
						 ) = ((
						SELECT	DECODE(w_idNewNodeCA, 0, TCVers.X1588_88_cmFarEndA, w_idNewNodeCA),
							-1,
							DECODE(w_idNewEqA, 0, TCVers.X1588_69_mychars, RPAD(w_idNewEqA, 13, ' ')),
							DECODE(w_idNewEqA, 0, TCVers.X1588_93_cmPath, -1),
							gt.new_pcp_id::CHAR(9) || 'P   L',
							-1
						FROM	GroupedTC gt
						WHERE	gt.tcvers_id = TCVers.id
						AND	gt.endAB = 0))
					WHERE	id IN (
						SELECT	tcvers_id
						FROM	GroupedTC
						WHERE	endAB = 0)
					;*/

					-- TCvers impactées à l'extrémité
											
					UPDATE t_media_links mdlk SET 
					b_node_id = CASE WHEN w_idNewNodeB = 0 THEN b_node_id ELSE w_idNewNodeB END,
					b_eqpt_id = CASE WHEN w_idNewEqB = 0 THEN b_eqpt_id ELSE w_idNewEqB END,
					mdlk_point_b_phys_end_type = 'P',
					b_port_id = gt.new_pcp_id
					FROM	GroupedTC gt
					WHERE	gt.mdlk_id = mdlk.mdlk_id
					AND	gt.endAB = 1;
						
					/*UPDATE	TCVers
					SET	(X1588_90_cmFarEndB,
						 X1588_87_cmFarEndA,
						 X1588_70_mychars,
						 X1588_93_cmPath,
						 X1588_55_mychars,
						 classId
						 ) = ((
						SELECT	DECODE(w_idNewNodeCB, 0, TCVers.X1588_90_cmFarEndB, w_idNewNodeCB),
							-1,
							DECODE(w_idNewEqB, 0, TCVers.X1588_70_mychars, RPAD(w_idNewEqB, 13, ' ')),
							DECODE(w_idNewEqB, 0, TCVers.X1588_93_cmPath, -1),
							gt.new_pcp_id::CHAR(9) || 'P   L',
							-1
						FROM	GroupedTC gt
						WHERE	gt.tcvers_id = TCVers.id
						AND	gt.endAB = 1))
					WHERE	id IN (
						SELECT	tcvers_id
						FROM	GroupedTC
						WHERE	endAB = 1)
					;*/
				END IF;


				-- -------------------------------------------------------------------------------------------------------
				-- Mise à jour des ressources logiques supportées par le (les) Lien(s) Support(s)
				-- Ici, on ne distingue pas les cas lien sur port isolé / lien sur port groupé, les traitements sont compatibles
				-- car les variables w_newExtA et w_newExtB contiennent l'ExtPort / l'ExtGroupe ad hoc en fct du cas de figure
				-- -------------------------------------------------------------------------------------------------------

				-- Mise a jour de toutes les TC et les TCVers impactees
				-- Pour endA et endB, classId = -1
				-- Pour farEndA et farEndB, farEndACid = -1
				-- Pour EqA et EqB, pathCid = -1
				-- Pour extA et ExtB, classId = -1 pour VP


				-- Ceux qui ont ptA en ExtA
				IF ((SELECT COUNT(*) FROM TCVersPtAEndA) != 0) THEN

					-- Modif du noeud -> TC
					/*IF (w_idNewNodeA != 0) THEN
						UPDATE	TC
						SET	X1563_1_cmNode = w_idNewNodeA,
							classId = -1,
							updateCounter = updateCounter + 1
						WHERE 	id IN (
							SELECT	idTC
							FROM	TCVersPtAEndA)
						;
					END IF;*/

					-- Modif du reste -> TCVers
					-- -2 ds patchCid pour ne pas verifier l'existence des manElem
					UPDATE t_res_prod_controlables
					SET a_node_id = CASE WHEN w_idNewNodeA = 0 THEN a_node_id ELSE w_idNewNodeA END,
						a_eqpt_id = CASE WHEN w_idNewEqA = 0 THEN a_eqpt_id ELSE w_idNewEqA END,
						a_pogr_id = CASE WHEN w_newExtA.typeExtPhys = 'G' THEN w_newExtA.pogr_id ELSE a_pogr_id END,
						a_port_id = CASE WHEN w_newExtA.typeExtPhys = 'P' THEN w_newExtA.port_id ELSE a_port_id END,
						rpct_point_a_phys_end_type = w_newExtA.typeExtPhys
					WHERE rpct_id IN ( SELECT t.rpct_id FROM TCVersPtAEndA t);
					
					/*UPDATE	TCVers
					SET	X1588_88_cmFarEndA = DECODE(w_idNewNodeCA, 0, X1588_88_cmFarEndA, w_idNewNodeCA),
						X1588_87_cmFarEndA = -1,
						X1588_69_mychars = DECODE(w_idNewEqA, 0, X1588_69_mychars, RPAD(w_idNewEqA, 13, ' ')),
						X1588_93_cmPath = DECODE(w_idNewEqA, 0, X1588_93_cmPath, -2),
						X1588_102_mychars = w_newExtA[1,13] || X1588_102_mychars[14,49],
						classId = -1,
						updateCounter = updateCounter + 1
					WHERE	id IN (
						SELECT	idTCVers
						FROM	TCVersPtAEndA)
					;*/

					-- Mise a jour table denormalisee
					-- portA a forcement changé, c'est un 'P' ou  un 'G'
					UPDATE	t_d_controlable_rscs
					SET	a_eqpt_id = CASE WHEN w_idNewEqA = 0 THEN a_eqpt_id ELSE w_idNewEqA END,
						a_port_id = CASE WHEN w_newExtA.typeExtPhys = 'G' THEN a_port_id ELSE w_newExtA.port_id END
					WHERE rpct_id IN ( SELECT t.rpct_id FROM TCVersPtAEndA t);
					
					/*UPDATE	brasilD_controlableRsc
					SET	logicalEqA = DECODE(w_idNewEqA, 0, logicalEqA, w_idNewEqA),
						portA = DECODE(w_newExtA[10], 'G', 0, w_newExtA[1,9]::INT)
					WHERE	id IN (
						SELECT	idTC
						FROM	TCVersPtAEndA)
					;*/
				END IF;

				-- Ceux qui ont ptB en ExtA
				-- Si port NPA, la table sera vide
				IF ((SELECT COUNT(*) FROM TCVersPtBEndA) != 0)THEN

					-- Modif du noeud -> TC
					/*IF (w_idNewNodeB != 0) THEN
						UPDATE	TC
						SET	X1563_1_cmNode = w_idNewNodeB,
							classId = -1,
							updateCounter = updateCounter + 1
						WHERE 	id IN (
							SELECT	idTC
							FROM	TCVersPtBEndA)
						;
					END IF;*/

					-- Modif du reste -> TCVers
					-- -2 ds path_cid pour ne pas verifier l'existence des manElem
					UPDATE t_res_prod_controlables
					SET a_node_id = CASE WHEN w_idNewNodeB = 0 THEN a_node_id ELSE w_idNewNodeB END,
						a_eqpt_id = CASE WHEN w_idNewEqB = 0 THEN a_eqpt_id ELSE w_idNewEqB END,
						a_pogr_id = CASE WHEN w_newExtB.typeExtPhys = 'G' THEN w_newExtB.pogr_id ELSE a_pogr_id END,
						a_port_id = CASE WHEN w_newExtB.typeExtPhys = 'P' THEN w_newExtB.port_id ELSE a_port_id END,
						rpct_point_a_phys_end_type = w_newExtB.typeExtPhys
					WHERE rpct_id IN ( SELECT t.rpct_id FROM TCVersPtBEndA t);
					
					/*UPDATE	TCVers
					SET	X1588_88_cmFarEndA = DECODE(w_idNewNodeCB, 0, X1588_88_cmFarEndA, w_idNewNodeCB),
						X1588_87_cmFarEndA = -1,
						X1588_69_mychars = DECODE(w_idNewEqB, 0, X1588_69_mychars, RPAD(w_idNewEqB, 13, ' ')),
						X1588_93_cmPath = DECODE(w_idNewEqB, 0, X1588_93_cmPath, -2),
						X1588_102_mychars = w_newExtB[1,13] || X1588_102_mychars[14,49],
						classId = -1,
						updateCounter = updateCounter + 1
					WHERE	id IN (
						SELECT	idTCVers
						FROM	TCVersPtBEndA)
					;*/

					-- Mise a jour table denormalisee
					-- portA a forcement changé, c'est un 'P' ou  un 'G'
					UPDATE	t_d_controlable_rscs
					SET	a_eqpt_id = CASE WHEN w_idNewEqB = 0 THEN a_eqpt_id ELSE w_idNewEqB END,
						a_port_id = CASE WHEN w_newExtB.typeExtPhys = 'G' THEN a_port_id ELSE w_newExtB.port_id END
					WHERE rpct_id IN ( SELECT t.rpct_id FROM TCVersPtBEndA t);
					
					/*UPDATE	brasilD_controlableRsc
					SET	logicalEqA = DECODE(w_idNewEqB, 0, logicalEqA, w_idNewEqB),
						portA = DECODE(w_newExtB[10], 'G', 0, w_newExtB[1,9]::INT)
					WHERE	id IN (
						SELECT	idTC
						FROM	TCVersPtBEndA)
					;*/
				END IF;


				-- Ceux qui ont ptA en ExtB, ce sont tous des VP
				IF ((SELECT COUNT(*) FROM TCVersPtAEndB) != 0)THEN

					-- Modif du noeud -> TC
					/*IF (w_idNewNodeA != 0) THEN
						UPDATE	TC
						SET	X1563_3_cmNode = w_idNewNodeA,
							classId = -1,
							updateCounter = updateCounter + 1
						WHERE 	id IN (
							SELECT	idTC
							FROM	TCVersPtAEndB)
						;
					END IF;*/

					-- Modif du reste -> TCVers
					-- -2 ds patchCid pour ne pas verifier l'existence des manElem
					UPDATE t_res_prod_controlables
					SET b_node_id = CASE WHEN w_idNewNodeA = 0 THEN b_node_id ELSE w_idNewNodeA END,
						b_eqpt_id = CASE WHEN w_idNewEqA = 0 THEN b_eqpt_id ELSE w_idNewEqA END,
						b_pogr_id = CASE WHEN w_newExtA.typeExtPhys = 'G' THEN w_newExtA.pogr_id ELSE b_pogr_id END,
						b_port_id = CASE WHEN w_newExtA.typeExtPhys = 'P' THEN w_newExtA.port_id ELSE b_port_id END,
						rpct_point_b_phys_end_type = w_newExtA.typeExtPhys
					WHERE rpct_id IN ( SELECT t.rpct_id FROM TCVersPtAEndB t);
					
					/*UPDATE	TCVers
					SET	X1588_90_cmFarEndB = DECODE(w_idNewNodeCA, 0, X1588_90_cmFarEndB, w_idNewNodeCA),
						X1588_87_cmFarEndA = -1,
						X1588_70_mychars = DECODE(w_idNewEqA, 0, X1588_70_mychars, RPAD(w_idNewEqA, 13, ' ')),
						X1588_93_cmPath = DECODE(w_idNewEqA, 0, X1588_93_cmPath, -2),
						X1588_55_mychars = w_newExtA[1,13] || X1588_55_mychars[14,20],
						classId = -1,
						updateCounter = updateCounter + 1
					WHERE	id IN (
						SELECT	idTCVers
						FROM	TCVersPtAEndB)
					;*/

					-- Modif de l'eqlB (ie newEqA du LS modifie) -> TCVers et MSPEntry (nip)
					IF (w_idNewEqA != 0) THEN

						-- Mise a jour des TCVers occupante (MRTAccesService) via AssResRel et ayant le outServPlOrderId = w_idOldEqA
						
						UPDATE	t_mrt_access_services
						SET 	eqpt_id = w_idNewEqA
						WHERE	mras_id IN (
							SELECT	mras_id
							FROM	t_resource_usages
							WHERE	rpct_id IN (SELECT	t.rpct_id FROM	TCVersPtAEndB t))
						AND	eqpt_id = w_idOldEqA;
						
						/*UPDATE	TCVers
						SET 	X1588_70_mychars = RPAD(w_idNewEqA, 13, ' '),
							updateCounter = updateCounter + 1
						WHERE	id IN (
							SELECT	X1569_1_cmAssembly
							FROM	AssResRel
							WHERE	X1569_3_cmResource IN (
								SELECT	idTC
								FROM	TCVersPtAEndB))
						AND	X1588_70_mychars = w_idOldEqA
						;*/

						-- Mise a jour des MSPEntry (RessourcePourDslamTstF) ayant moVersion = w_idTCVers et versId = w_idOldEqA
						UPDATE t_res_prod_roles 
						SET  nip_eqpt_id = w_idNewEqA 
						WHERE rpct_id IN (SELECT t.rpct_id FROM	TCVersPtAEndB t)
						AND nip_eqpt_id = w_idOldEqA;
						
						
						/*UPDATE	MSPEntry
						SET	X1095_1_intval = w_idNewEqA,
							updateCounter = updateCounter + 1
						WHERE	X1095_9_mMoVersion IN (
							SELECT	idTCVers
							FROM	TCVersPtAEndB)
						AND	X1095_1_intval = w_idOldEqA
						;*/

						-- Mise a jour table denormalisee
						UPDATE	t_d_controlable_rscs
						SET	b_eqpt_id = w_idNewEqA
						WHERE rpct_id IN ( SELECT t.rpct_id FROM TCVersPtAEndB t);
						
						/*UPDATE	brasilD_controlableRsc
						SET	logicalEqB = w_idNewEqA
						WHERE	id IN (
							SELECT	idTC
							FROM	TCVersPtAEndB)
						;*/
					END IF;
				END IF;

				-- Ceux qui ont ptB en ExtB, ce sont tous des VP
				-- Attention cas particulier pour mise a jour extB si portNPA
				IF ((SELECT COUNT(*) FROM TCVersPtBEndB) != 0)THEN

					-- Modif du noeud -> TC
					/*IF (w_idNewNodeB != 0) THEN
						UPDATE	TC
						SET	X1563_3_cmNode = w_idNewNodeB,
							classId = -1,
							updateCounter = updateCounter + 1
						WHERE 	id IN (
							SELECT	idTC
							FROM	TCVersPtBEndB)
						;
					END IF;*/

					-- Modif du reste -> TCVers
					-- -2 ds patchCid pour ne pas verifier l'existence des manElem
					-- Cas d'un port
					UPDATE t_res_prod_controlables 
					SET b_node_id = CASE WHEN w_idNewNodeB = 0 THEN b_node_id ELSE w_idNewNodeB END,
						b_eqpt_id = CASE WHEN w_idNewEqB = 0 THEN b_eqpt_id ELSE w_idNewEqB END,
						b_pogr_id = CASE WHEN w_newExtB.typeExtPhys = 'G' THEN w_newExtB.pogr_id ELSE b_pogr_id END,
						b_port_id = CASE WHEN w_newExtB.typeExtPhys = 'P' THEN w_newExtB.port_id ELSE b_port_id END,
						
						rpct_point_b_ce_shelf_num = CASE WHEN w_newExtB.typeExtPhys = 'N' THEN w_newExtB.ce_shelf_num ELSE rpct_point_b_ce_shelf_num END,
						rpct_point_b_ce_card_num = CASE WHEN w_newExtB.typeExtPhys = 'N' THEN w_newExtB.ce_card_num ELSE rpct_point_b_ce_card_num END,
						rpct_point_b_ce_port_num = CASE WHEN w_newExtB.typeExtPhys = 'N' THEN w_newExtB.ce_port_num ELSE rpct_point_b_ce_port_num END,
						ce_eqpt_id = CASE WHEN w_newExtB.typeExtPhys = 'N' THEN w_newExtB.ce_eqpt_id ELSE ce_eqpt_id END,
						rpct_point_b_phys_end_type = w_newExtB.typeExtPhys
					WHERE rpct_id IN ( SELECT t.rpct_id FROM TCVersPtBEndB t);
					
					/*UPDATE	TCVers
					SET	X1588_90_cmFarEndB = DECODE(w_idNewNodeCB, 0, X1588_90_cmFarEndB, w_idNewNodeCB),
						X1588_87_cmFarEndA = -1,
						X1588_70_mychars = DECODE(w_idNewEqB, 0, X1588_70_mychars, RPAD(w_idNewEqB, 13, ' ')),
						X1588_93_cmPath = DECODE(w_idNewEqB, 0, X1588_93_cmPath, -2),
						X1588_55_mychars = DECODE(w_newExtB[10],
									'N', w_newExtB[1,17] || X1588_55_mychars[18,20],
									 w_newExtB[1,13] || X1588_55_mychars[14,20]),
						classId = -1,
						updateCounter = updateCounter + 1
					WHERE	id IN (
						SELECT	idTCVers
						FROM	TCVersPtBEndB)
					;*/

					-- Modif de l'eqlB (ie newEqB du LS modifie)  -> TCVers et MSPEntry (nip)
					IF (w_idNewEqB != 0) THEN

						-- Mise a jour des TCVers occupante (MRTAccesService) via AssResRel et ayant le outServPlOrderId = w_idOldEqB
						UPDATE	t_mrt_access_services
						SET 	eqpt_id = w_idNewEqB
						WHERE	mras_id IN (
							SELECT	mras_id
							FROM	t_resource_usages
							WHERE	rpct_id IN (SELECT	t.rpct_id FROM	TCVersPtBEndB t))
						AND	eqpt_id = w_idOldEqB;
						
						/*UPDATE	TCVers
						SET 	X1588_70_mychars = RPAD(w_idNewEqB, 13, ' '),
							updateCounter = updateCounter + 1
						WHERE	id IN (
							SELECT	X1569_1_cmAssembly
							FROM	AssResRel
							WHERE	X1569_3_cmResource IN (
								SELECT	idTC
								FROM	TCVersPtBEndB))
						AND	X1588_70_mychars = w_idOldEqB
						;*/

						-- Mise a jour des MSPEntry (RessourcePourDslamTstF) ayant moVersion = w_idTCVers et versId = w_idOldEqB
						UPDATE t_res_prod_roles 
						SET  nip_eqpt_id = w_idNewEqB 
						WHERE rpct_id IN (SELECT t.rpct_id FROM	TCVersPtBEndB t)
						AND nip_eqpt_id = w_idOldEqB;
						
						
						/*UPDATE	MSPEntry
						SET	X1095_1_intval = w_idNewEqB,
							updateCounter = updateCounter + 1
						WHERE	X1095_9_mMoVersion IN (
							SELECT	idTCVers
							FROM	TCVersPtBEndB)
						AND	X1095_1_intval = w_idOldEqB
						;*/

						-- Mise a jour table denormalisee
						UPDATE	t_d_controlable_rscs
						SET	b_eqpt_id = w_idNewEqB
						WHERE rpct_id IN ( SELECT t.rpct_id FROM TCVersPtBEndB t);
						
						/*UPDATE	brasilD_controlableRsc
						SET	logicalEqB = w_idNewEqB
						WHERE	id IN (
							SELECT	idTC
							FROM	TCVersPtBEndB)
						;*/
					END IF;

				END IF;

			END IF;

		END IF;

	END IF;

	DROP TABLE TCVersPtAEndA;
	DROP TABLE TCVersPtAEndB;
	DROP TABLE TCVersPtBEndA;
	DROP TABLE TCVersPtBEndB;
	DROP TABLE GroupedPCP;
	DROP TABLE GroupedTC;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_ptsextls;
--/
CREATE FUNCTION sp_t_media_links_ptsextls (p_oldaddinfo brasiltype_addinfo, p_newaddinfo brasiltype_addinfo, p_oldbpartner brasiltype_addinfo, p_newbpartner brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE

	w_nbUtil1 INT;
	w_nbUtil2 INT;
	w_nbUtil INT;
	w_nbPortNPA INT;
	w_typeExtB CHAR(1);

	--listeAddInfo BrasilType_AddInfo[2];
	nbreUpdatedLigne INT := 0;
BEGIN	
	
	IF (NOT(p_newAddInfo IS NULL OR p_newBPartner IS  NULL)) THEN
		IF (p_oldAddInfo IS NULL OR p_oldBPartner IS NULL) THEN

			w_typeExtB := p_newBPartner.typeExtPhys;


			-- ExtB = ExtPort
			IF (w_typeExtB='P') THEN

				-- Calcul du nombre d'utilisateur du point en extrémité A
				SELECT COUNT(*) INTO w_nbUtil1 FROM t_media_links 
				WHERE (a_port_id  = p_newAddInfo.port_id 
						--AND  mdlk_point_a_interface_type = p_newAddInfo.typeInterface -- tjrs = 'L'
						--AND rpct_point_a_interface_id = p_newAddInfo.interfaceId
						AND mdlk_point_a_phys_end_type = 'P') 
				OR (a_port_id  = p_newBPartner.port_id 
						--AND  mdlk_point_a_interface_type = p_newBPartner.typeInterface -- tjrs = 'L'
						--AND rpct_point_a_interface_id = p_newBPartner.interfaceId
						AND mdlk_point_a_phys_end_type = 'P');

				-- Calcul du nombre d'utilisateur du point en extrémité B
				SELECT COUNT(*) INTO w_nbUtil2 FROM t_media_links 
				WHERE (b_port_id  = p_newAddInfo.port_id 
						--AND  mdlk_point_b_interface_type = p_newAddInfo.typeInterface -- tjrs = 'L'
						--AND rpct_point_b_interface_id = p_newAddInfo.interfaceId
						AND mdlk_point_b_phys_end_type = 'P') 
				OR (b_port_id  = p_newBPartner.port_id 
						--AND  mdlk_point_b_interface_type = p_newBPartner.typeInterface -- tjrs = 'L'
						--AND rpct_point_b_interface_id = p_newBPartner.interfaceId
						AND mdlk_point_b_phys_end_type = 'P');

				w_nbUtil := w_nbUtil1+w_nbUtil2;

				-- Si deja utilise par un lien support
				IF (w_nbUtil!=0) THEN
					PERFORM brasil_raiseException(11, '61');
				END IF;

				--RAISE NOTICE 'PortA <%>, PortB <%>',p_newAddInfo.port_id,p_newBPartner.port_id;
				-- Maj des 2 ports
				UPDATE t_ports SET port_occup_ont=port_occup_ont+1 WHERE port_id=p_newAddInfo.port_id OR port_id=p_newBPartner.port_id;
					
				GET DIAGNOSTICS nbreUpdatedLigne = ROW_COUNT;

				-- Si un des 2 points n'existe pas
				IF (nbreUpdatedLigne!=2) THEN
					PERFORM brasil_raiseException(11, '62');
				END IF;

			ELSE
				-- ExtB = ExtPortNPA
				IF (w_typeExtB='N') THEN
	
					-- Si port NPA non unique
					SELECT COUNT(*) INTO w_nbPortNPA FROM t_media_links 
						WHERE ce_eqpt_id = p_newBPartner.ce_eqpt_id  
						AND mdlk_point_b_ce_shelf_num = p_newBPartner.ce_shelf_num 
						AND mdlk_point_b_ce_card_num = p_newBPartner.ce_card_num 
						AND mdlk_point_b_ce_port_num = p_newBPartner.ce_port_num
						AND mdlk_point_b_phys_end_type = 'N'
						--AND mdlk_point_b_interface_type = p_newBPartner.typeInterface -- tjrs = 'L'
						;
						
					IF (w_nbPortNPA!=0) THEN
						PERFORM brasil_raiseException(11, '63');
					END IF;

				END IF;

				-- Verification pour ExtA
				-- Calcul du nombre d'utilisateur
				SELECT COUNT(*) INTO w_nbUtil1 FROM t_media_links 
				WHERE a_port_id  = p_newAddInfo.port_id 
						--AND  mdlk_point_a_interface_type = p_newAddInfo.typeInterface -- tjrs = 'L'
						--AND rpct_point_a_interface_id = p_newAddInfo.interfaceId
						AND mdlk_point_a_phys_end_type = 'P';

				SELECT COUNT(*) INTO w_nbUtil2 FROM t_media_links 
				WHERE (ce_eqpt_id = p_newAddInfo.ce_eqpt_id  
						AND mdlk_point_b_ce_shelf_num = p_newAddInfo.ce_shelf_num 
						AND mdlk_point_b_ce_card_num = p_newAddInfo.ce_card_num 
						AND mdlk_point_b_ce_port_num = p_newAddInfo.ce_port_num
						AND mdlk_point_b_phys_end_type = 'N'
						--AND mdlk_point_b_interface_type = p_newAddInfo.typeInterface -- tjrs = 'L'
						)
				OR (mdlk_point_b_phys_end_type = 'E' 
					--AND mdlk_point_b_interface_type= p_newAddInfo.typeInterface -- tjrs = 'L' 
					AND mdlk_point_b_cust_eqpt_info = p_newAddInfo.mdlk_point_b_cust_eqpt_info);

				w_nbUtil := w_nbUtil1+w_nbUtil2;

				-- Si deja utilise par un lien support
				IF (w_nbUtil!=0) THEN
					PERFORM brasil_raiseException(11, '61');
				END IF;

				-- Maj de ExtA
				UPDATE t_ports SET port_occup_ont=port_occup_ont+1 WHERE port_id=p_newAddInfo.port_id;

				GET DIAGNOSTICS nbreUpdatedLigne = ROW_COUNT;
				-- Si le point n'existe pas
				IF (nbreUpdatedLigne!=1) THEN
					PERFORM brasil_raiseException(11, '62');
				END IF;

			END IF;
		END IF;
	END IF;

	/*IF (p_newClassId = -1) THEN
		LET w_classId = p_oldClassId;
		LET w_extA = p_newAddInfo;
		LET w_extB = p_newBPartner;
	ELSE
		LET w_classId = p_newClassId;
		IF (p_oldAddInfo IS NULL OR p_oldBPartner IS NULL) THEN
			listeAddInfo[0] = p_newAddInfo;
			listeAddInfo[1] = p_newBPartner;
		ELSE
			listeAddInfo[0] = p_oldAddInfo;
			listeAddInfo[1] = p_oldBPartner;
		END IF;
	--END IF;


	RETURN listeAddInfo; --w_extA, w_extB, w_classId;*/

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_uniqlientrans;
--/
CREATE FUNCTION sp_t_media_links_uniqlientrans (p_oldfunctioncode bigint, p_newfunctioncode bigint, p_oldintserialno character, p_newintserialno character, p_oldfarenda bigint, p_newfarenda bigint, p_oldfarendb bigint, p_newfarendb bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	IF (p_oldFunctionCode = 0 OR p_oldIntSerialNo = '2147483647' OR p_oldFarEndA = 0 OR p_oldFarEndB = 0) THEN
		-- Cas de l'insertion
		IF (p_newFunctionCode != 0 AND p_newIntSerialNo != '2147483647' AND p_newFarEndA != 0 AND p_newFarEndB != 0) THEN

			PERFORM sp_t_media_links_checkUniqLienTrans(p_newFunctionCode, p_newIntSerialNo, p_newFarEndA, p_newFarEndB);

		END IF;

	-- Cas de modification
	ELSE

		IF (p_oldFunctionCode != p_newFunctionCode OR p_oldIntSerialNo != p_newIntSerialNo OR
			p_oldFarEndA != p_newFarEndA OR p_oldFarEndB != p_newFarEndB ) THEN

			PERFORM sp_t_media_links_checkUniqLienTrans(p_newFunctionCode, p_newIntSerialNo, p_newFarEndA, p_newFarEndB);

		END IF;
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_update;
--/
CREATE FUNCTION sp_t_media_links_update ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	oldAddInfoA BrasilType_AddInfo;
	newAddInfoA BrasilType_AddInfo;
	listeAddInfo BrasilType_AddInfo[2];

	oldAddInfoB BrasilType_AddInfo;
	newAddInfoB BrasilType_AddInfo;
BEGIN
	-- Modif extremite A ou extremite B
	oldAddInfoA.port_id := old.a_port_id;
	oldAddInfoA.typeExtPhys := old.mdlk_point_a_phys_end_type;
	--oldAddInfoA.typeInterface := old.mdlk_point_a_interface_type;
	--oldAddInfoA.interfaceId := old.mdlk_point_a_interface_id;
	
	newAddInfoA.port_id := new.a_port_id;
	newAddInfoA.typeExtPhys := new.mdlk_point_a_phys_end_type;
	--newAddInfoA.typeInterface := new.mdlk_point_a_interface_type;
	--newAddInfoA.interfaceId := new.mdlk_point_a_interface_id;
	
	oldAddInfoB.port_id := old.b_port_id;
	oldAddInfoB.ce_eqpt_id := old.ce_eqpt_id;
	oldAddInfoB.typeExtPhys := old.mdlk_point_b_phys_end_type;
	--oldAddInfoB.typeInterface := old.mdlk_point_b_interface_type;
	--oldAddInfoB.interfaceId := old.mdlk_point_b_interface_id;
	oldAddInfoB.ce_eqpt_id := old.ce_eqpt_id;
	oldAddInfoB.ce_shelf_num := old.mdlk_point_b_ce_shelf_num;
	oldAddInfoB.ce_card_num := old.mdlk_point_b_ce_card_num;
	oldAddInfoB.ce_port_num := old.mdlk_point_b_ce_port_num;
	oldAddInfoB.mdlk_point_b_cust_eqpt_info := old.mdlk_point_b_cust_eqpt_info;
	
	newAddInfoB.port_id := new.b_port_id;
	newAddInfoB.ce_eqpt_id := new.ce_eqpt_id;
	newAddInfoB.typeExtPhys := new.mdlk_point_b_phys_end_type;
	--newAddInfoB.typeInterface := new.mdlk_point_b_interface_type;
	--newAddInfoB.interfaceId := new.mdlk_point_b_interface_id;
	newAddInfoB.ce_eqpt_id := new.ce_eqpt_id;
	newAddInfoB.ce_shelf_num := new.mdlk_point_b_ce_shelf_num;
	newAddInfoB.ce_card_num := new.mdlk_point_b_ce_card_num;
	newAddInfoB.ce_port_num := new.mdlk_point_b_ce_port_num;
	newAddInfoB.mdlk_point_b_cust_eqpt_info := new.mdlk_point_b_cust_eqpt_info;

	-- Cas d'un lien support
	PERFORM sp_t_media_links_ptsExtLS(oldAddInfoA, newAddInfoA, oldAddInfoB, newAddInfoB);
	/*listeAddInfo := f_t_media_links_ptsExtLS(old.oldAddInfoA, new.newAddInfoA, old.oldAddInfoB, new.newAddInfoB);
	
	new.a_port_id := listeAddInfo[0].port_id;
	new.mdlk_point_a_phys_end_type := listeAddInfo[0].typeExtPhys;
	new.mdlk_point_a_interface_type := listeAddInfo[0].typeInterface;
	new.mdlk_point_a_interface_id := listeAddInfo[0].interfaceId;
	
	new.b_port_id := listeAddInfo[1].port_id;
	new.ce_eqpt_id := listeAddInfo[1].ce_eqpt_id;
	new.mdlk_point_b_phys_end_type := listeAddInfo[1].typeExtPhys;
	new.mdlk_point_b_interface_type := listeAddInfo[1].typeInterface;
	new.mdlk_point_b_interface_id := listeAddInfo[1].interfaceId;
	new.ce_eqpt_id := listeAddInfo[1].ce_eqpt_id;
	new.mdlk_point_b_ce_shelf_num := listeAddInfo[1].ce_shelf_num;
	new.mdlk_point_b_ce_card_num := listeAddInfo[1].ce_card_num;
	new.mdlk_point_b_ce_port_num := listeAddInfo[1].ce_port_num;*/
	

	
	-- Modif equipement A ou equipement B

	/*WHEN (new.X1588_52_mychars IN ("L","D","W","I","V"))
		(EXECUTE PROCEDURE brasil_TCVers_checkEqsExt(old.X1588_52_mychars, new.X1588_52_mychars, old.X1588_69_mychars, new.X1588_69_mychars, old.X1588_70_mychars, new.X1588_70_mychars, old.X1588_93_cmPath, new.X1588_93_cmPath)
			INTO X1588_69_mychars, X1588_70_mychars, X1588_93_cmPath),*/
		--EXECUTE PROCEDURE brasil_TCVers_checkEqsExt(old.rpct_type, new.rpct_type, old.a_eqpt_id, new.a_eqpt_id, old.b_eqpt_id, new.b_eqpt_id, old.X1588_93_cmPath, new.X1588_93_cmPath)

	-- Unicite lien de trans
		PERFORM sp_t_media_links_uniqLienTrans(
			old.fctc_id, new.fctc_id, old.mdlk_serial_num, new.mdlk_serial_num, old.a_node_id, new.a_node_id,
			old.b_node_id, new.b_node_id);
			/*brasil_TCVers_uniqLienTrans(old.X1588_52_mychars, new.X1588_52_mychars,
			old.X1588_57_ctionCode, new.X1588_57_ctionCode, old.X1588_50_mychars, new.X1588_50_mychars, old.X1588_88_cmFarEndA, new.X1588_88_cmFarEndA,
			old.X1588_90_cmFarEndB, new.X1588_90_cmFarEndB, new.X1588_87_cmFarEndA);*/

	-- Modif noeudA ou noeudB
	/*IF (old.a_node_id != 0 AND old.b_node_id != 0) THEN
		--WHEN (new.X1588_87_cmFarEndA != -1 AND old.X1588_88_cmFarEndA != 0 AND old.X1588_90_cmFarEndB != 0)
		--(EXECUTE FUNCTION brasil_TC_notUpdate_FarEndAFarEndB(old.X1588_88_cmFarEndA, old.X1588_90_cmFarEndB) INTO X1588_88_cmFarEndA, X1588_90_cmFarEndB),
		new.a_node_id := old.a_node_id;
		new.b_node_id := old.b_node_id;
	END IF;*/

	
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_media_links_updatepoint;
--/
CREATE FUNCTION sp_t_media_links_updatepoint (p_idoldpt bigint, p_idnewpt bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE 
	w_oldPtUsageCounter INT;
	w_oldPort_logical_occup_cpt smallint;
	w_nbreLigne INT;
	w_oldPtNbMRTAD INT;
BEGIN
	-- L'ancien port ne doit pas etre occupe par une MRTAccesDslam

	
	SELECT count(*) INTO w_oldPtNbMRTAD FROM t_mrt_access_dslams WHERE a_port_id = p_idOldPt AND mrtd_point_a_phys_end_type = 'P';

	IF (w_oldPtNbMRTAD != 0) THEN
		PERFORM brasil_raiseException(11, '86');
	END IF;


	SELECT	port_occup_ont,
			port_logical_occup_cpt
	INTO	w_oldPtUsageCounter,
			w_oldPort_logical_occup_cpt
	FROM	t_ports
	WHERE	port_id = p_idOldPt;

	-- Mise a jour du nouveau port en verifiant qu'il est libre et qu'il n'est pas groupe
	UPDATE	t_ports
	SET		port_occup_ont = w_oldPtUsageCounter,
			port_logical_occup_cpt = w_oldPort_logical_occup_cpt
	WHERE	port_id = p_idNewPt
		AND	(port_occup_ont IS NULL OR port_occup_ont = 0)
		AND	(port_logical_occup_cpt IS NULL OR port_logical_occup_cpt = 0);

	GET DIAGNOSTICS w_nbreLigne = ROW_COUNT; 
	-- Le point n'existe pas ou ne repond pas au critere
	IF (w_nbreLigne = 0) THEN
		PERFORM brasil_raiseException(11, '84');
	END IF;


	-- Mise a jour de l'ancien port en verifiant qu'il n'est pas dans un groupe
	UPDATE	t_ports
	SET		port_occup_ont = 0,
			port_logical_occup_cpt = 0
	WHERE	port_id = p_idOldPt;

	GET DIAGNOSTICS w_nbreLigne = ROW_COUNT; 
	-- Le point n'existe pas ou ne repond pas au critere
	IF (w_nbreLigne = 0) THEN
		PERFORM brasil_raiseException(11, '85');
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_dslam_deletemrtvers;
--/
CREATE FUNCTION sp_t_mrt_access_dslam_deletemrtvers (p_idmrtvers bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN

		-- REM : updateCounter pas incrémenté ici car fait dans le service irwas
		UPDATE	t_making_files
		SET		mkfl_mrt_impact_size = mkfl_mrt_impact_size - 1
		WHERE	mkfl_id IN (
			SELECT	mkfl_id
			FROM	t_mrt_vers_impacts
			WHERE	mrdv_id = p_idMRTVers
		);
	
		DELETE
		FROM	t_mrt_vers_impacts
		WHERE	mrdv_id = p_idMRTVers;
		
		DELETE FROM t_epc_vers_comps WHERE	mrdv_id = p_idMRTVers;

	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_dslam_vers_del;
--/
CREATE FUNCTION sp_t_mrt_access_dslam_vers_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	PERFORM sp_t_mrt_access_dslam_deleteMRTVers(OLD.mrdv_id);
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_dslams_checkandupdatenewl;
--/
CREATE FUNCTION sp_t_mrt_access_dslams_checkandupdatenewl (p_mrtd_info_portgp_tmp character)  RETURNS bigint
  VOLATILE
AS $dbvis$
DECLARE
	w_port_group_name CHARACTER(3);
	w_port_group_type CHAR(1);
	w_nb_ports INT;
	w_id_port_maitre INT;
	w_pogr_group_id INT;
BEGIN
	--RAISE NOTICE ' -------- Debut sp_t_mrt_access_dslams_checkAndUpdateNewL';
	
	w_port_group_name := substring(p_mrtd_info_portgp_tmp FROM 1 FOR 3);
	w_port_group_type := substring(p_mrtd_info_portgp_tmp FROM 4 FOR 1);
	w_nb_ports := substring(p_mrtd_info_portgp_tmp FROM 5 FOR 1)::INT;
	w_id_port_maitre := substring(p_mrtd_info_portgp_tmp FROM 6 FOR 9)::INT;
	
	-- Creation table temporaire pour stocker les id des Ports
	DROP TABLE IF EXISTS tmp_table_ports ;
	CREATE TEMP TABLE tmp_table_ports(w_id_port bigint);
	
	-- Recuperation des identifiants des ports
	FOR w_index IN 2..w_nb_ports LOOP
		INSERT INTO tmp_table_ports VALUES(substr(p_mrtd_info_portgp_tmp,6+9*(w_index-1),9)::bigint);
	END LOOP;
	
	-- Verification de l'existance du groupe de port
	--BRASIL-440 - ini:
	--SELECT pg.pogr_id
	--FROM t_port_groups pg, t_ports p
	--INTO w_pogr_group_id
	--WHERE pg.pogr_id=p.pogr_id
	--AND p.card_id = (SELECT card_id FROM t_ports WHERE port_id = w_id_port_maitre)
	--AND pg.pogr_name = w_port_group_name;
	
	SELECT pg.pogr_id
	  FROM t_port_groups pg
	  JOIN t_ports p ON pg.pogr_id=p.pogr_id
	  INTO w_pogr_group_id
	 WHERE p.card_id = (SELECT card_id FROM t_ports WHERE port_id = w_id_port_maitre)
	   AND pg.pogr_name = w_port_group_name;
	--BRASIL-440 - fin:
	-- Si le groupe de port n'existe pas, alors on l'insere
	IF (NOT FOUND) THEN
		
		-- Insertion du nouveau groupe de port
		INSERT INTO t_port_groups (pogr_name, pogr_group_type, pogr_management_policy) 
		VALUES (w_port_group_name, w_port_group_type, 'L') 
		RETURNING pogr_id 
		INTO STRICT w_pogr_group_id;
		
		-- Modification du groupe de port dans la table t_mrt_access_dslams
		/*UPDATE t_mrt_access_dslams 
		SET a_pogr_id = w_pogr_group_id 
		WHERE mrtd_id = p_mrtd_id;
		*/
		-- Modification du groupe de port dans la table t_ports (port maitre)
		UPDATE t_ports 
		SET pogr_id = w_pogr_group_id, port_quality = 'M', port_occup_ont = port_occup_ont + 1, port_logical_occup_cpt = 1
		WHERE port_id = w_id_port_maitre;
		
		-- Modification du groupe de port dans la table t_ports (ports esclaves)
		UPDATE t_ports 
		SET pogr_id = w_pogr_group_id, port_quality = 'S', port_occup_ont = port_occup_ont + 1 , port_logical_occup_cpt = 1 
		WHERE port_id 
		IN (
			SELECT w_id_port 
			FROM tmp_table_ports
		); 
	ELSE
		PERFORM brasil_raiseException(11, '44');
	END IF;
	
	--RAISE NOTICE ' -------- Fin sp_t_mrt_access_dslams_checkAndUpdateNewL';
	
	RETURN w_pogr_group_id;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_dslams_del;
--/
CREATE FUNCTION sp_t_mrt_access_dslams_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	oldAddInfoA BrasilType_AddInfo;
BEGIN

	oldAddInfoA.port_id := old.a_port_id;
	oldAddInfoA.pogr_id := old.a_pogr_id;
	oldAddInfoA.typeExtPhys := old.mrtd_point_a_phys_end_type;
	oldAddInfoA.typeInterface := old.mrtd_interface_type;
	oldAddInfoA.interfaceId := old.mrtd_point_a_interface_id;
	
	PERFORM sp_t_mrt_access_dslams_suppressionModuleSFP(oldAddInfoA);
	PERFORM sp_t_mrt_access_dslams_delMRTDslam(oldAddInfoA);
	--PERFORM sp_t_mrt_access_dslams_delEPCSupport(old.mrtd_id);
		
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_dslams_delmrtdslam;
--/
CREATE FUNCTION sp_t_mrt_access_dslams_delmrtdslam (p_addinfo brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	-- ExtA=ExtPort
	IF (p_AddInfo.typeExtPhys='P') THEN
		PERFORM sp_updateOldP(p_AddInfo.port_id);

	-- ExtA=ExtGroupe
	ELSIF (p_AddInfo.typeExtPhys='G') THEN
		PERFORM sp_updateOldG(p_AddInfo.pogr_id);

	-- ExtA=ExtGroupeListe
	ELSE
		PERFORM sp_t_mrt_access_dslams_updateOldL(p_AddInfo.pogr_id);

	END IF;
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_dslams_ins_update;
--/
CREATE FUNCTION sp_t_mrt_access_dslams_ins_update ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	newAddInfoA BrasilType_AddInfo;

	oldAddInfoA BrasilType_AddInfo;
	w_pogr_id BIGINT;
	w_mrtd_info_portgp_tmp CHARACTER(255);
BEGIN
	
	newAddInfoA.port_id := new.a_port_id;
	newAddInfoA.typeExtPhys := new.mrtd_point_a_phys_end_type;
	newAddInfoA.typeInterface := new.mrtd_interface_type;
	newAddInfoA.interfaceId := new.mrtd_point_a_interface_id;
	newAddInfoA.pogr_id := new.a_pogr_id;
	w_mrtd_info_portgp_tmp := new.mrtd_info_portgp_tmp;
	--RAISE NOTICE '----------- TG_OP <%>',TG_OP;
	IF(TG_OP = 'UPDATE') THEN
		oldAddInfoA.port_id := old.a_port_id;
		oldAddInfoA.typeExtPhys := old.mrtd_point_a_phys_end_type;
		oldAddInfoA.typeInterface := old.mrtd_interface_type;
		oldAddInfoA.interfaceId := old.mrtd_point_a_interface_id;
		oldAddInfoA.pogr_id := old.a_pogr_id;
		w_mrtd_info_portgp_tmp := '';
	END IF;

	w_pogr_id := f_t_mrt_access_dslams_ptsExtMRTDslam(oldAddInfoA, newAddInfoA, w_mrtd_info_portgp_tmp);
	IF(w_pogr_id != 0) THEN
		new.a_pogr_id := w_pogr_id;
	END IF;
	-- Vider le champ temporaire
	new.mrtd_info_portgp_tmp := ''; 
	
	-- Pas besoin de réecrire cette procedure en G8, car les champs de la table ServiceContPers sont intégrés dans la table t_mrt_access_dslams
	-- EXECUTE PROCEDURE brasil_TCVers_duplicateIdMRTDslam("", new.X1588_52_mychars, 0, new.X1588_4_eContainer, 0, new.X1077_43_respondMO)
			
	-- Gestion equipements extremites
	/*IF (new.a_eqpt_id!="" AND new.b_eqpt_id!="") THEN
		sp_checkEqs(new.a_eqpt_id, new.b_eqpt_id);
	END IF;*/
	
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_dslams_suppressionmodulesfp;
--/
CREATE FUNCTION sp_t_mrt_access_dslams_suppressionmodulesfp (p_addinfo brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_pogr_id BIGINT;
	w_pogr_id2 BIGINT;
	w_typeModule CHAR(10);
	W_EtatPort  SMALLINT;	
	w_Port BIGINT;
	W_NumPort SMALLINT;
	W_IncNumPort INT;
	W_IdCarte BIGINT;
	w_idPort BIGINT;
	w_idPort2 BIGINT;
	w_idTechnoFTTH BIGINT;
	w_idTechno BIGINT;
	w_isTechnoFTTH INT;
	
	w_idTechnoRecord RECORD;
	w_PortRecord RECORD;
BEGIN	
	w_isTechnoFTTH = 0;
		
	IF (p_AddInfo.typeExtPhys = 'P') THEN
		w_idPort := p_AddInfo.port_id;
		w_pogr_id := 0;
		--w_groupeName = '';
		--W_IdCarte = 0;
	ELSE		
		w_idPort := 0;
		w_pogr_id := p_AddInfo.pogr_id;
		--W_IdCarte =  p_AddInfo.card_id;
	END IF;
		
	--RAISE NOTICE '========== w_idPort = % w_pogr_id = %',w_idPort,w_pogr_id;
		
    SELECT tcty_id FROM t_technology_types INTO w_idTechnoFTTH WHERE tcty_name like 'FTTH%';	
	
	--Cas d'un port simple
   IF (w_idPort != 0) THEN
     --BRASIL-440 - ini:
     --SELECT sfp.sfmp_mode   FROM t_sfp_modules sfp,t_sfp_module_port_assocs ass INTO w_typeModule 
	 --	WHERE ass.sfpm_id=sfp.sfpm_id AND ass.port_id = w_idPort;
	 SELECT sfp.sfmp_mode   
  	   FROM t_sfp_modules sfp
	   JOIN t_sfp_module_port_assocs ass ON ass.sfpm_id=sfp.sfpm_id 
	   INTO w_typeModule 
	  WHERE ass.port_id = w_idPort;
	 --BRASIL-440 - fin:	
		
		--Récupération de l'id carte
	  --BRASIL-440 - ini:	
	  --SELECT  c.card_id  FROM  t_cards c,  t_ports pc  INTO W_IdCarte WHERE c.card_id = pc.card_id  AND pc.port_id = w_idPort;
	  SELECT c.card_id  
 	    FROM t_cards c
	    JOIN t_ports pc ON c.card_id = pc.card_id
	    INTO W_IdCarte 
	   WHERE pc.port_id = w_idPort;
	  --BRASIL-440 - fin:
		
		
		/*SELECT   tcnp.tcty_id FROM  t_techno_on_card_nat_profiles tcnp JOIN t_card_national_profiles cnp ON tcnp.cnpr_id = cnp.cnpr_id
			JOIN t_cards c ON cnp.csfv_id = c.csfv_id 
			INTO w_idTechno WHERE c.card_id = W_IdCarte AND  tcnp.tcty_id  = w_idTechnoFTTH;
		*/
		FOR  w_idTechnoRecord IN SELECT tcnp.tcty_id as idTechno  
			FROM  t_techno_on_card_nat_profiles tcnp JOIN t_card_national_profiles cnp ON tcnp.cnpr_id = cnp.cnpr_id
			JOIN t_cards c ON cnp.csfv_id = c.csfv_id 
				WHERE c.card_id = W_IdCarte	
		LOOP	
			w_idTechno := w_idTechnoRecord.idTechno;
			 IF (w_idTechno = w_idTechnoFTTH) THEN
	             	w_isTechnoFTTH := 1;
	             	EXIT;
			  END IF;				  
		END LOOP;
		
		IF (w_isTechnoFTTH != 1) THEN
				--Module de type single
			IF (w_typeModule = 'SINGLE') THEN
				 DELETE FROM t_sfp_module_port_assocs WHERE port_id = w_idPort;
			END IF;
			--Module de type dual
			IF (w_typeModule = 'DUAL') THEN
				--  verifier que le port suivant est libre si le port est impair
				SELECT port_num FROM t_ports p INTO W_NumPort WHERE p.port_id = w_idPort;			 
				
				
				IF  (NOT(W_NumPort IS NULL)) THEN
					IF  ( mod(W_NumPort,2) = 0) THEN
						--Cas d'un port paire,verifier si le port inferieur est libre
						W_IncNumPort := W_NumPort - 1;			
					ELSE
						--Cas d'un port impaire ,verifier si le port superieur est libre
					 	W_IncNumPort := W_NumPort + 1;
					END IF;
					
					--BRASIL-440 - ini:
				    --SELECT  pc.port_attribuable,pc.port_id  FROM  t_cards c,  t_ports pc INTO W_EtatPort,w_idPort2       
				    --    WHERE c.card_id = pc.card_id
				    --    AND pc.port_num= W_IncNumPort
		  			--	AND  c.card_id = W_IdCarte;
		  			SELECT pc.port_attribuable,pc.port_id  
					  FROM t_cards c
					  JOIN t_ports pc ON c.card_id = pc.card_id
					  INTO W_EtatPort,w_idPort2       
					 WHERE pc.port_num= W_IncNumPort
					   AND  c.card_id = W_IdCarte;
					--BRASIL-440 - fin:
		  				
		             -- SI le port associé n'est pas occupé alors on effectue la suppression du module        			  
		             IF (W_EtatPort != 4) THEN
		             	 DELETE FROM t_sfp_module_port_assocs WHERE port_id IN (w_idPort, w_idPort2);
					 END IF;
				 END IF;
			END IF;		
		END IF;
   END IF;
   
    --Cas d'un groupe de ports
   IF (w_pogr_id  != 0) THEN
   			SELECT MAX(p.card_id) FROM t_ports p JOIN t_port_groups gr ON p.pogr_id=gr.pogr_id INTO W_IdCarte WHERE p.pogr_id = w_pogr_id;
   			
			FOR  w_idTechnoRecord IN SELECT tcnp.tcty_id as idTechno  
				FROM  t_techno_on_card_nat_profiles tcnp JOIN t_card_national_profiles cnp ON tcnp.cnpr_id = cnp.cnpr_id 
				JOIN t_cards c ON cnp.csfv_id = c.csfv_id
					WHERE  c.card_id = W_IdCarte	
			LOOP	
				w_idTechno := w_idTechnoRecord.idTechno;
				 IF (w_idTechno = w_idTechnoFTTH) THEN
		             	w_isTechnoFTTH := 1;
		             	EXIT;
				  END IF;				  
			END LOOP;
		--RAISE NOTICE '========== w_isTechnoFTTH = %',w_isTechnoFTTH;
		IF (w_isTechnoFTTH != 1) THEN
			
	   		FOR  w_PortRecord IN 
	   		--BRASIL-440 - ini:
	   		--SELECT  pc.port_id as port_id  FROM  t_cards c,  t_ports pc        
			--			WHERE c.card_id = pc.card_id AND pc.pogr_id = w_pogr_id AND c.card_id = W_IdCarte LOOP
			--			
			--	w_Port := w_PortRecord.port_id;
			SELECT pc.port_id as port_id  
			  FROM t_cards c
			  JOIN t_ports pc ON c.card_id = pc.card_id 
			 WHERE pc.pogr_id = w_pogr_id 
				AND c.card_id = W_IdCarte LOOP						
							w_Port := w_PortRecord.port_id;
			--BRASIL-440 - fin:			
				--BRASIL-440 - ini:
				--SELECT sfp.sfmp_mode  FROM t_sfp_modules sfp,t_sfp_module_port_assocs ass INTO w_typeModule
				--WHERE ass.sfpm_id=sfp.sfpm_id AND port_id = w_Port;
				SELECT sfp.sfmp_mode  
				  FROM t_sfp_modules sfp
				  JOIN t_sfp_module_port_assocs ass ON ass.sfpm_id=sfp.sfpm_id 
				  INTO w_typeModule
				 WHERE port_id = w_Port;
				 --BRASIL-440 - fin:
				--RAISE NOTICE '========== w_typeModule <%> w_Port <%>',w_typeModule,w_Port;
						--Module de type single
				IF (w_typeModule = 'SINGLE') THEN
					 DELETE FROM t_sfp_module_port_assocs WHERE port_id = w_Port;
				END IF;
				--Module de type dual
				IF (w_typeModule = 'DUAL') THEN
					--  verifier que le port suivant est libre si le port est impair
					SELECT port_num FROM t_ports p INTO W_NumPort WHERE p.port_id = w_Port;	
							 
					
					IF  (NOT(W_NumPort IS NULL)) THEN
						IF  ( mod(W_NumPort,2) = 0) THEN
							--Cas d'un port paire,verifier si le port inferieur est libre
							W_IncNumPort := W_NumPort - 1;			
						ELSE 
							--Cas d'un port impaire ,verifier si le port superieur est libre
							W_IncNumPort := W_NumPort + 1;
						END IF;	
						--BRASIL-440 - ini:
						--SELECT  pc.port_attribuable,pc.port_id, pg.pogr_id FROM  t_cards c, t_ports pc, t_port_groups pg   INTO W_EtatPort,w_idPort2,w_pogr_id2    
				        --WHERE c.card_id = pc.card_id
						--AND pc.pogr_id = pg.pogr_id
				        --AND pc.port_num= W_IncNumPort
		  				--AND  c.card_id = W_IdCarte;
		  				SELECT pc.port_attribuable,pc.port_id, pg.pogr_id 
						  FROM t_cards c
						  JOIN t_ports pc ON c.card_id = pc.card_id
						  JOIN t_port_groups pg ON pc.pogr_id = pg.pogr_id
						  INTO W_EtatPort,w_idPort2,w_pogr_id2    
						 WHERE pc.port_num= W_IncNumPort
							AND c.card_id = W_IdCarte;
		  				--BRASIL-440 - fin:
		  											
						 -- SI le port associé est occupé alors on n'effectue pas la suppression du module (Autre client)       			  
						 IF (W_EtatPort != 4 OR w_pogr_id2 = w_pogr_id) THEN
							DELETE FROM t_sfp_module_port_assocs WHERE port_id IN (w_Port, w_idPort2);
						 END IF;
					 END IF;
				END IF; 				
			END LOOP;	
		END IF;
   END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_dslams_updateoldl;
--/
CREATE FUNCTION sp_t_mrt_access_dslams_updateoldl (p_pogr_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN	


	-- Envoi de l'ordre de suppression du groupeListe via araliaName
/*
	UPDATE $EMS1DB:PCP SET updateCounter=updateCounter+1, X3010_13_intval=X3010_13_intval-1,
	X3010_15_mychars= "DG L" || p_nomList WHERE X3029_8_cmEquip=p_idEquip AND X3029_17_mychars LIKE w_speedComp;
*/

	UPDATE t_ports SET pogr_id = NULL, port_quality = NULL, port_occup_ont = port_occup_ont - 1, port_logical_occup_cpt = 0 WHERE pogr_id = p_pogr_id;
	--UPDATE t_mrt_access_dslams mrt SET mrt.a_pogr_id = NULL WHERE mrt.a_pogr_id = p_pogr_id;
	DELETE FROM t_port_groups  WHERE pogr_id = p_pogr_id;
	

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_service_vers_del;
--/
CREATE FUNCTION sp_t_mrt_access_service_vers_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	PERFORM sp_t_mrt_access_service_vers_deleteMRTVers(OLD.mrsv_id);
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_service_vers_deletemrtvers;
--/
CREATE FUNCTION sp_t_mrt_access_service_vers_deletemrtvers (p_idmrtvers bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN

		-- suppression des impacts
		-- REM : updateCounter pas incrémenté ici car fait dans le service irwas
		UPDATE	t_making_files
		SET		mkfl_mrt_impact_size = mkfl_mrt_impact_size - 1
		WHERE	mkfl_id IN (
			SELECT	mkfl_id
			FROM	t_mrt_vers_impacts
			WHERE	mrsv_id = p_idMRTVers
		);
	
		DELETE
		FROM	t_mrt_vers_impacts
		WHERE	mrsv_id = p_idMRTVers;
		
		DELETE FROM t_epc_vers_comps WHERE	mrsv_id = p_idMRTVers;

	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_services_del;
--/
CREATE FUNCTION sp_t_mrt_access_services_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	ressourceUsageId BIGINT;
BEGIN
	RAISE NOTICE ' -------- Fin sp_t_mrt_access_services_del';
	
	-- Selectionner l'ID de la RU à supprimer
	SELECT tr_id INTO ressourceUsageId FROM t_resource_usages WHERE mras_id= OLD.mras_id;
	
	--Suppression des ressources Usages de la table t_resource_usages	
	DELETE FROM t_resource_usages WHERE mras_id = OLD.mras_id;
	
	-- Suppression des ressources techniques
	DELETE  FROM t_trs where tr_id = ressourceUsageId ;
	
	--Suppression des versions de la table t_mrt_access_service_vers
	DELETE FROM	t_mrt_access_service_vers WHERE	mras_id = OLD.mras_id;
	
	--RAISE NOTICE ' -------- Fin sp_t_mrt_access_services_del';
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_access_services_update;
--/
CREATE FUNCTION sp_t_mrt_access_services_update ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	w_rpct_id BIGINT;
BEGIN
	RAISE NOTICE ' -------- Debut sp_t_mrt_access_services_update';
	RAISE NOTICE ' -------- old.mras_utilisation : %, new.mras_utilisation : %',old.mras_utilisation,new.mras_utilisation;
	
	IF(old.mras_utilisation IS NOT NULL AND  old.mras_utilisation IS DISTINCT FROM new.mras_utilisation) THEN
		FOR w_rpct_id IN SELECT rpct_id FROM t_d_controlable_rscs WHERE t_d_controlable_rscs.ctrs_type <> 'V'
						AND t_d_controlable_rscs.rpct_id in (SELECT rpct_id FROM t_resource_usages WHERE mras_id = old.mras_id)
		LOOP
			PERFORM brasil_updateCompteursVlan(w_rpct_id);
		END LOOP;
	END IF;
	RAISE NOTICE ' -------- Fin sp_t_mrt_access_services_update';
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_vers_impacts_checkmrtversimpact;
--/
CREATE FUNCTION sp_t_mrt_vers_impacts_checkmrtversimpact (p_mrtserviceversid bigint, p_mrtdslamversid bigint, p_initialstate character, p_currentstate character)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN

	IF (p_mrtServiceVersId IS NOT NULL) THEN
		UPDATE t_mrt_access_service_vers SET mrsv_current_state = p_currentState WHERE mrsv_id = p_mrtServiceVersId AND mrsv_current_state = p_initialState;
	END IF;
	
	IF (p_mrtDslamVersId IS NOT NULL) THEN
		UPDATE t_mrt_access_dslam_vers SET mrdv_current_state = p_currentState WHERE mrdv_id = p_mrtDslamVersId AND mrdv_current_state = p_initialState;
	END IF;

	IF (NOT FOUND) THEN
		PERFORM brasil_raiseException(11, '17');
	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_vers_impacts_ins;
--/
CREATE FUNCTION sp_t_mrt_vers_impacts_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
		-- FSC T-142 : horodatage de tables en BDD Brasil
		NEW.mrvi_creation_time = clock_timestamp(); 
		PERFORM sp_t_mrt_vers_impacts_checkMRTVersImpact(NEW.mrsv_id, NEW.mrdv_id, NEW.mrvi_initial_status, NEW.mrvi_current_status);
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_vers_impacts_upd_currentstate;
--/
CREATE FUNCTION sp_t_mrt_vers_impacts_upd_currentstate ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	IF (NEW.mrvi_current_status != OLD.mrvi_current_status) THEN
		PERFORM sp_t_mrt_vers_impacts_updateMRTVersState(NEW.mrsv_id, NEW.mrdv_id, NEW.mrvi_current_status);
	END IF;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_mrt_vers_impacts_updatemrtversstate;
--/
CREATE FUNCTION sp_t_mrt_vers_impacts_updatemrtversstate (p_mrtserviceversid bigint, p_mrtdslamversid bigint, p_newcurrentstate character)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	IF (p_mrtServiceVersId IS NOT NULL) THEN
		UPDATE t_mrt_access_service_vers SET mrsv_current_state = p_newCurrentState WHERE mrsv_id = p_mrtServiceVersId;
	END IF;
	
	IF (p_mrtDslamVersId IS NOT NULL) THEN
		UPDATE t_mrt_access_dslam_vers SET mrdv_current_state = p_newCurrentState WHERE mrdv_id = p_mrtDslamVersId;
	END IF;
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_computeopstate;
--/
CREATE FUNCTION sp_t_ports_computeopstate (p_port_logical_occup_cpt smallint, p_port_out_status character, p_port_pin_num smallint, p_strp_id bigint, p_port_prod_status character, p_pogr_id bigint)  RETURNS smallint
  VOLATILE
AS $dbvis$
DECLARE
	w_opState INT;
	w_occupLogique INT;
BEGIN
	RAISE NOTICE ' -------- Debut SP sp_t_ports_computeOpState';
	
	-- Port occupé
	IF (p_port_logical_occup_cpt > 0) THEN
		w_opState := 4;
	ELSE
		IF (p_pogr_id IS NOT NULL) THEN
			w_opState := 0;
		ELSE
			-- Port pre-cable et en service
			IF (p_strp_id IS NOT NULL  AND (p_port_out_status IS NULL OR p_port_out_status = ' ' OR p_port_out_status ='P')) THEN
				IF (p_port_prod_status = 'O') THEN
					w_opState := 1;
				ELSIF (p_port_prod_status = 'M') THEN
					w_opState := 2;
				ELSE
					w_opState := 3;
				END IF;
			ELSE
					w_opState := 0;
			END IF;
		END IF;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_ports_computeOpState';
	RETURN w_opState;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_del;
--/
CREATE FUNCTION sp_t_ports_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut sp_t_ports_del';
	IF(OLD.strp_id IS NOT NULL) THEN
		PERFORM brasil_raiseException(11, '53');		
	END IF;
	--RAISE NOTICE ' -------- Fin sp_t_ports_del';
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_handledatafordtable;
--/
CREATE FUNCTION sp_t_ports_handledatafordtable (p_idcard bigint, p_idstripe bigint, p_stripe_module character, p_stripe_uprange smallint, p_stripe_downrange smallint, p_stripe_uplevel smallint, p_stripe_downlevel smallint, p_incr integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_infoStripe CHAR(25);
	w_nbPort INT;
	w_dslamId INT;
	w_module CHAR(1);
	w_upRange SMALLINT; 
	w_downRange SMALLINT; 
	w_upLevel SMALLINT; 
	w_downLevel SMALLINT;
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_ports_handleDataForDTable';
	IF (p_incr < 0) THEN
		SELECT xdcs_port_count INTO w_nbPort FROM t_d_xdsl_card_stripes WHERE card_id = p_idCard AND strp_id = p_idStripe;

		IF (w_nbPort = 1) THEN
			DELETE FROM t_d_xdsl_card_stripes WHERE card_id = p_idCard AND strp_id = p_idStripe;
		ELSE
			-- Mise a jour de la table
			UPDATE t_d_xdsl_card_stripes SET xdcs_port_count = xdcs_port_count - 1 WHERE card_id = p_idCard AND strp_id = p_idStripe;
		END IF;
	ELSE
	-- Mise a jour de la table
		UPDATE t_d_xdsl_card_stripes SET xdcs_port_count = xdcs_port_count + 1 WHERE card_id = p_idCard AND strp_id = p_idStripe;
		IF (NOT FOUND) THEN
			-- La relation n'existe pas encore, on l'insere
			-- Verif qu'on a les infos de la reglette
			IF (p_stripe_module = '' OR p_stripe_upRange = 0 OR p_stripe_downRange = 0 OR p_stripe_upLevel = 0 OR p_stripe_downLevel = 0) THEN
				SELECT strp_module, strp_up_range, strp_down_range, strp_up_level, strp_down_level
				INTO w_module, w_upRange, w_downRange, w_upLevel, w_downLevel
				FROM t_stripes WHERE strp_id = p_idStripe;
			ELSE
				w_module := p_stripe_module;
				w_upRange := p_stripe_upRange; 
				w_downRange := p_stripe_downRange; 
				w_upLevel := p_stripe_upLevel; 
				w_downLevel := p_stripe_downLevel;
			END IF;

			-- Recuperation du dslam_id de la carte
			-- BRASIL-440 - ini:
			--SELECT sh.eqpt_id INTO w_dslamId FROM t_cards c, t_slots s, t_shelfs sh WHERE c.slot_id=s.slot_id AND s.shlf_id=sh.shlf_id AND c.card_id = p_idCard;
			SELECT sh.eqpt_id INTO w_dslamId FROM t_cards c JOIN t_slots s ON c.slot_id=s.slot_id JOIN t_shelfs sh ON s.shlf_id=sh.shlf_id WHERE c.card_id = p_idCard;
			-- BRASIL-440 - fin:

			INSERT INTO t_d_xdsl_card_stripes(card_id, strp_id, eqpt_id, xdcs_port_count, xdcs_module, xdcs_up_range, xdcs_down_range, xdcs_up_level, xdcs_down_level)
			 VALUES(p_idCard, p_idStripe, w_dslamId, 1, w_module, w_upRange, w_downRange, w_upLevel, w_downLevel);
		END IF;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_ports_handleDataForDTable';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_initopstate;
--/
CREATE FUNCTION sp_t_ports_initopstate ()  RETURNS integer
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_ports_initOpState';
	RETURN 0;
	--RAISE NOTICE ' -------- Fin SP sp_t_ports_initOpState';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_ins;
--/
CREATE FUNCTION sp_t_ports_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	RAISE NOTICE ' -------- Debut SP sp_t_ports_ins';
	-- FSC T-142 : horodatage de tables en BDD Brasil
	NEW.port_creation_time = clock_timestamp(); 
	NEW.port_out_status := ' ';
	NEW.port_pin_num := 0;
	NEW.strp_id := NULL;
	NEW.port_prod_status := 'O';
	NEW.port_attribuable := 0;
	RAISE NOTICE ' -------- Fin SP sp_t_ports_ins';
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_modifinfosport;
--/
CREATE FUNCTION sp_t_ports_modifinfosport (p_idport bigint, p_idcard bigint, p_old_port_out_status character, p_old_port_pin_num smallint, p_old_strp_id bigint, p_old_port_prod_status character, p_new_port_out_status character, p_new_port_pin_num smallint, p_new_strp_id bigint, p_new_port_prod_status character, p_usagecounter integer, p_pcpfunc smallint, p_port_logical_occup_cpt smallint, p_pogr_id bigint)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE
	w_idReg INT;
	w_depthReg INT;
	w_heightReg INT;
	w_nameReg CHAR(25);
	w_ucReg INT;
	w_araliaPort CHAR(13);
	w_opState INT;
	w_araliaStrp_id CHAR(9);
	w_araliaPort_pin_num CHAR(4);
	w_module CHAR(1);
	w_upRange SMALLINT; 
	w_downRange SMALLINT; 
	w_upLevel SMALLINT; 
	w_downLevel SMALLINT;
	nbreUpdatedLigne INT := 0;
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_ports_modifInfosPort';
	-- Mise a jour du pre-cablage
	IF (p_old_strp_id IS DISTINCT FROM p_new_strp_id OR p_old_port_pin_num != p_new_port_pin_num) THEN

		-- Si port occupe par une MRT AD, pas le droit de supprimer le pre-cablage
		IF (p_pcpFunc != 2 AND p_port_logical_occup_cpt != 0 AND p_new_strp_id = 0) THEN
			IF ((SELECT COUNT(*) FROM t_mrt_access_dslams WHERE a_port_id = p_idPort AND mrtd_runtime_type = 'D' ) != 0) THEN
				PERFORM  brasil_raiseException(11, '47');
			END IF;
		END IF;
	
		-- Mise a jour du nombre de broches libres de l'ancienne reglette
		-- Seulement si on change de reglette, sinon c'est un changement de broche
		IF (p_old_strp_id IS NOT NULL AND p_old_strp_id IS DISTINCT FROM p_new_strp_id) THEN
			UPDATE t_stripes SET strp_free_pin_count = strp_free_pin_count + 1 WHERE strp_id = p_old_strp_id;

			-- Si port, mise a jour de la table pour recherche de broche
			IF (p_pcpFunc != 2) THEN
				PERFORM  sp_t_ports_handleDataForDTable(p_idCard, p_old_strp_id, '', 0::SMALLINT, 0::SMALLINT, 0::SMALLINT, 0::SMALLINT, -1);
			END IF;
		END IF;
		
		-- Traitement nouvelle reglette
		IF (p_new_strp_id IS NOT NULL) THEN
			w_idReg = p_new_strp_id;
			w_araliaStrp_id = p_new_strp_id || '%';
			w_araliaPort_pin_num = p_new_port_pin_num || '%';

			-- Recuperation infos reglette
			SELECT strp_free_pin_count, strp_pin_count, strp_module, strp_up_range, strp_down_range, strp_up_level, strp_down_level 
			INTO w_depthReg, w_heightReg, w_module, w_upRange, w_downRange, w_upLevel, w_downLevel 
			FROM t_stripes WHERE strp_id = w_idReg;

			-- SubPos inexistante
			IF (NOT FOUND) THEN
				PERFORM brasil_raiseException(11, '48');

			-- NumBroche invalide
			ELSIF (p_new_port_pin_num >= w_heightReg) THEN
				PERFORM brasil_raiseException(11, '49');

			-- NumBroche non unique sur reglette
			ELSIF ((SELECT COUNT(*) FROM t_ports WHERE strp_id = p_new_strp_id AND port_pin_num = p_new_port_pin_num) != 0) THEN
				--PERFORM  brasil_raiseException(11, '50');

			END IF;
			
			
			-- Maj de la nouvelle reglette, seulement si on a change de reglette
			-- Sinon c'est un changement de broche
			IF (p_old_strp_id IS DISTINCT FROM p_new_strp_id) THEN
				UPDATE t_stripes SET strp_free_pin_count = w_depthReg - 1
				 WHERE strp_id = w_idReg;

				 GET DIAGNOSTICS nbreUpdatedLigne = ROW_COUNT;

				-- SubPos supprimee entre le select et le update
				IF (nbreUpdatedLigne = 0) THEN
					PERFORM brasil_raiseException(11, 'Reglette d id '||w_idReg||' inexistante');
				END IF;

				-- Si port, mise a jour de la table pour recherche de broche
				IF (p_pcpFunc != 2) THEN
					PERFORM sp_t_ports_handleDataForDTable(p_idCard, w_idReg, w_module, w_upRange, w_downRange, w_upLevel, w_downLevel, 1);
				END IF;
			END IF;
		END IF;
	END IF;
			
	-- Calcul de l'operationalState
	-- Ce n'est pas un port
	IF (p_pcpFunc = 2) THEN
		w_opState := 0;
	ELSE
		SELECT sp_t_ports_computeOpState(p_port_logical_occup_cpt, p_new_port_out_status, p_new_port_pin_num, p_new_strp_id, p_new_port_prod_status, p_pogr_id) INTO w_opState;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_ports_modifInfosPort';
	RETURN w_opState;	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_upd_aralianamepcpinterface;
--/
CREATE FUNCTION sp_t_ports_upd_aralianamepcpinterface ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_ports_upd_araliaNamePcpInterface';
	-- Maj valeur par defaut de l'araliaName et de l'argOs
	--RAISE NOTICE ' -----NEW.port_out_status <%>, OLD.port_out_status <%>, NEW.pogr_id <%>, NEW.port_id <%>',NEW.port_out_status, OLD.port_out_status,NEW.pogr_id,NEW.port_id;
	
	IF (NEW.port_out_status = '' AND NEW.port_pin_num = 0 AND NEW.strp_id IS NULL AND NEW.port_prod_status = '') THEN
		NEW.port_out_status := ' ';
		NEW.port_pin_num := 0;
		NEW.strp_id := NULL;
		NEW.port_prod_status := 'O';
		NEW.port_attribuable := 0;
	END IF;	

	-- Changement occupation d'un port
	IF (OLD.port_logical_occup_cpt IS DISTINCT FROM NEW.port_logical_occup_cpt AND NEW.port_out_status = OLD.port_out_status
		AND NEW.port_pin_num = OLD.port_pin_num AND NEW.strp_id IS NOT DISTINCT FROM OLD.strp_id) THEN
		SELECT sp_t_ports_computeOpState(NEW.port_logical_occup_cpt, OLD.port_out_status, OLD.port_pin_num, OLD.strp_id, OLD.port_prod_status, NEW.pogr_id) INTO NEW.port_attribuable;
	END IF;	
	-- Modification des infos du port
	IF (NEW.port_out_status IS DISTINCT FROM OLD.port_out_status OR NEW.port_pin_num != OLD.port_pin_num OR NEW.strp_id IS DISTINCT FROM OLD.strp_id OR NEW.port_prod_status IS DISTINCT FROM OLD.port_prod_status) THEN
		SELECT sp_t_ports_modifInfosPort(NEW.port_id, NEW.card_id,OLD.port_out_status, OLD.port_pin_num, OLD.strp_id, OLD.port_prod_status, NEW.port_out_status, NEW.port_pin_num, NEW.strp_id, 
		NEW.port_prod_status, OLD.port_occup_ont, OLD.port_activation_status, OLD.port_logical_occup_cpt, OLD.pogr_id) INTO NEW.port_attribuable;
	END IF;
	--RAISE NOTICE ' -------- Fin sp_t_ports_upd_araliaNamePcpInterface';
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_upd_pcpfunc;
--/
CREATE FUNCTION sp_t_ports_upd_pcpfunc ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut sp_t_ports_upd_pcpFunc';
	IF(NEW.port_activation_status IS DISTINCT FROM OLD.port_activation_status) THEN
		SELECT sp_t_ports_updFunc(OLD.port_id, OLD.port_activation_status, NEW.port_activation_status,NEW.port_occup_ont, 
							  OLD.port_out_status, OLD.port_pin_num, OLD.strp_id, OLD.port_prod_status, 
							  NEW.port_out_status, NEW.port_pin_num, NEW.strp_id, NEW.port_prod_status, 
							  NEW.card_id,NEW.port_logical_occup_cpt, NEW.pogr_id)
			INTO NEW.port_attribuable;
	END IF;
	--RAISE NOTICE ' -------- Fin sp_t_ports_upd_pcpFunc';	
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_upd_usagecounter;
--/
CREATE FUNCTION sp_t_ports_upd_usagecounter ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut sp_t_ports_upd_usageCounter';
		-- Occupation d'un shadow port interdite
	IF (OLD.port_occup_ont = 0 AND NEW.port_occup_ont > 0 AND OLD.port_activation_status = 2) THEN
		PERFORM brasil_raiseException(11, '52');
		
	-- Mise a jour de la table bookedPort lors de la première occupation
	ELSIF (OLD.port_occup_ont = 0 AND NEW.port_occup_ont > 0) THEN
		PERFORM sp_t_ports_updateBookedPort(OLD.port_id);
	END IF;
	
	IF (NEW.port_occup_ont = 0) THEN
		NEW.port_occup_status := 0;
		NEW.port_occupation_status := 0;
	ELSE
		NEW.port_occup_status = 1;
		IF(NEW.port_logical_occup_cpt IS NULL OR NEW.port_logical_occup_cpt = 0) THEN
			NEW.port_occupation_status := 1;
		ELSE
			NEW.port_occupation_status := 2;
		END IF;
	END IF;

	--RAISE NOTICE ' -------- Fin sp_t_ports_upd_usageCounter';
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_updatebookedport;
--/
CREATE FUNCTION sp_t_ports_updatebookedport (p_portid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut sp_t_ports_updateBookedPort';
	DELETE FROM t_d_booked_ports WHERE port_id = p_portId;
	--RAISE NOTICE ' -------- Fin sp_t_ports_updateBookedPort';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_ports_updfunc;
--/
CREATE FUNCTION sp_t_ports_updfunc (p_idport bigint, p_oldfunc smallint, p_newfunc smallint, p_usagecounter integer, p_old_port_out_status character, p_old_port_pin_num smallint, p_old_strp_id bigint, p_old_port_prod_status character, p_new_port_out_status character, p_new_port_pin_num smallint, p_new_strp_id bigint, p_new_port_prod_status character, p_newequipid bigint, p_port_logical_occup_cpt smallint, p_pogr_id bigint)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE
	w_opState INT;
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_ports_updFunc';
	-- Cas de la suppression d'une carte
	IF (p_oldFunc = 1 AND p_newFunc = 2 AND p_usageCounter != 0) THEN
		PERFORM brasil_raiseException(11, '51');
	END IF;

	-- Insertion d'une carte (n'etait pas port et le devient + le port est pre-cable)
	IF (p_oldFunc = 2 AND p_newFunc = 1 AND p_new_strp_id != 0) THEN
		PERFORM sp_t_ports_handleDataForDTable(p_newEquipId, p_new_strp_id, '',0::SMALLINT, 0::SMALLINT, 0::SMALLINT, 0::SMALLINT, 1);
	END IF;

	-- Ce n'est pas un port
	IF (p_newFunc = 2) THEN
		w_opState = 0;
	ELSE
		SELECT sp_t_ports_computeOpState(p_port_logical_occup_cpt, p_new_port_out_status, p_new_port_pin_num, p_new_strp_id, p_new_port_prod_status, p_pogr_id) INTO w_opState;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_ports_updFunc';
	RETURN w_opState;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_chekandupdateext;
--/
CREATE FUNCTION sp_t_res_prod_controlables_chekandupdateext (p_new_ext brasiltype_addinfo, p_old_ext brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nbUtilA INT;
	w_nbUtilAA1 INT;
	w_nbUtilAA2 INT;
	w_nbUtilAB2 INT;
BEGIN
		
	SELECT COUNT(*) FROM t_mrt_access_dslams INTO w_nbUtilAA1 WHERE 
	a_pogr_id = CASE WHEN p_new_Ext.typeExtPhys = 'P' THEN a_pogr_id ELSE p_new_Ext.pogr_id END
	AND a_port_id = CASE WHEN p_new_Ext.typeExtPhys = 'G' THEN a_port_id ELSE p_new_Ext.port_id END
	AND mrtd_interface_type = 'D';

		
	SELECT COUNT(*) FROM t_res_prod_controlables INTO w_nbUtilAA2 WHERE
	a_pogr_id = CASE WHEN p_new_Ext.typeExtPhys = 'P' THEN a_pogr_id ELSE p_new_Ext.pogr_id END
	AND a_port_id = CASE WHEN p_new_Ext.typeExtPhys = 'G' THEN a_port_id ELSE p_new_Ext.port_id END
	AND rpct_point_a_phys_end_type = p_new_Ext.typeExtPhys
	AND rpct_point_a_interface_type = p_new_Ext.typeInterface
	AND rpct_point_a_interface_id = CASE WHEN p_new_Ext.interfaceId IS NOT NULL THEN p_new_Ext.interfaceId ELSE rpct_point_a_interface_id END ;


	SELECT COUNT(*) FROM t_res_prod_controlables INTO w_nbUtilAB2 WHERE
	b_pogr_id = CASE WHEN p_new_Ext.typeExtPhys = 'P' THEN b_pogr_id ELSE p_new_Ext.pogr_id END
	AND b_port_id = CASE WHEN p_new_Ext.typeExtPhys = 'G' THEN b_port_id ELSE p_new_Ext.port_id END
	AND rpct_point_b_phys_end_type = p_new_Ext.typeExtPhys
	AND rpct_point_b_interface_type = p_new_Ext.typeInterface
	AND rpct_point_b_interface_id = CASE WHEN p_new_Ext.interfaceId IS NOT NULL THEN p_new_Ext.interfaceId ELSE rpct_point_b_interface_id END  ;
	
	
	w_nbUtilA := w_nbUtilAA1 + w_nbUtilAA2 + w_nbUtilAB2;
	IF (w_nbUtilA != 0) THEN
		PERFORM brasil_raiseException(11, '64');
	END IF;


	-- Mise a jour de la nouvelle extA

	-- ExtA=ExtPort
	IF ( p_new_Ext.typeExtPhys='P') THEN
		PERFORM sp_checkAndUpdateNewP(p_new_Ext.port_id, 1);

	-- ExtA=ExtGroupe
	ELSE
		PERFORM sp_checkAndUpdateNewG(p_new_Ext.pogr_id, 1);
	END IF;


	-- Liberation de l'ancienne ExtA

	-- ExtA=ExtPort
	IF (p_old_Ext.typeExtPhys='P') THEN
		PERFORM sp_updateOldP(p_old_Ext.port_id);

	-- ExtA=ExtGroupe
	ELSE
		PERFORM sp_updateOldG(p_old_Ext.pogr_id);
	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_del;
--/
CREATE FUNCTION sp_t_res_prod_controlables_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	oldAddInfo BrasilType_AddInfo;
	newAddInfo BrasilType_AddInfo;
	bPartner BrasilType_AddInfo;
BEGIN
	oldAddInfo.port_id := old.a_port_id;
	oldAddInfo.pogr_id := old.a_pogr_id;
	oldAddInfo.typeExtPhys := old.rpct_point_a_phys_end_type;
	oldAddInfo.typeInterface := old.rpct_type;
	
	bPartner.port_id := old.b_port_id;
	bPartner.pogr_id := old.b_pogr_id;
	bPartner.typeExtPhys := old.rpct_point_b_phys_end_type;
	bPartner.typeInterface := old.rpct_type;
	
	-- Cas d'une ressourceProdControlable
	CASE
	WHEN (OLD.rpct_type IN ('W', 'I', 'V')) THEN
		PERFORM sp_t_res_prod_controlables_delResProdControlable(old.rpct_id);
	ELSE
	-- ne rien faire
    END CASE;
	
	CASE
	-- Cas d'une interface
	WHEN (OLD.rpct_type = 'I') THEN
		PERFORM sp_t_res_prod_controlables_delInterface(old.rpct_point_a_phys_end_type, old.a_port_id, old.a_pogr_id);
	-- Cas d'un VLAN
	WHEN (OLD.rpct_type = 'W') THEN
		PERFORM sp_t_res_prod_controlables_delInterface(old.rpct_point_a_phys_end_type, old.a_port_id, old.a_pogr_id);
		PERFORM sp_t_res_prod_controlables_rank(oldAddInfo , newAddInfo);
	-- Cas d'un VP
	WHEN (OLD.rpct_type = 'V') THEN
		PERFORM sp_t_res_prod_controlables_delVP(oldAddInfo, bPartner);
	ELSE
	-- ne rien faire
    END CASE;
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_delinterface;
--/
CREATE FUNCTION sp_t_res_prod_controlables_delinterface (p_rpct_point_a_phys_end_type character, p_a_port_id bigint, p_a_pogr_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	-- ExtA=ExtPort
	IF (p_rpct_point_a_phys_end_type='P') THEN
		PERFORM sp_updateOldP(p_a_port_id);

	-- ExtA=ExtGroupe
	ELSE
		PERFORM sp_updateOldG(p_a_pogr_id);

	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_delresprodcontrolable;
--/
CREATE FUNCTION sp_t_res_prod_controlables_delresprodcontrolable (p_rpct_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_rpctId BIGINT;
BEGIN
	/*IF ((SELECT COUNT(*) FROM t_res_prod_roles WHERE rpct_id = p_rpct_id) != 0) THEN
		PERFORM brasil_raiseException(11, '68');
	END IF;*/
--RAISE NOTICE '-------------------------DEBUT sp_t_res_prod_controlables_delResProdControlable p_rpct_id= <%>',p_rpct_id;
	DELETE FROM t_resource_usages WHERE rpct_id = p_rpct_id;
	DELETE FROM t_d_controlable_rscs WHERE rpct_id = p_rpct_id;
	DELETE FROM t_d_rsc_vcis WHERE rpct_id = p_rpct_id;
	DELETE FROM t_vc_lock_ranges WHERE rpct_id = p_rpct_id;
	DELETE FROM t_d_rsc_dslam_tsfs WHERE rpct_id = p_rpct_id;
	DELETE FROM t_d_need_new_vcs WHERE rpct_id = p_rpct_id;
--RAISE NOTICE '-------------------------FIN sp_t_res_prod_controlables_delResProdControlable';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_delvp;
--/
CREATE FUNCTION sp_t_res_prod_controlables_delvp (p_addinfo brasiltype_addinfo, p_bpartner brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE '--------------- p_AddInfo.pogr_id = % p_bPartner.pogr_id = %',p_AddInfo.pogr_id,p_bPartner.pogr_id; 
	-- ExtA=ExtPort
	IF (p_AddInfo.typeExtPhys='P') THEN
		PERFORM sp_updateOldP(p_AddInfo.port_id);

	-- ExtA=ExtGroupe
	ELSE
		PERFORM sp_updateOldG(p_AddInfo.pogr_id);

	END IF;

	-- ExtB=ExtPort
	IF (p_bPartner.typeExtPhys='P') THEN
		PERFORM sp_updateOldP(p_bPartner.port_id);

	-- ExtB=ExtGroupe
	ELSIF (p_bPartner.typeExtPhys='G') THEN
		PERFORM sp_updateOldG(p_bPartner.pogr_id);

	END IF;
	-- ExtB=ExtPortNPA -> rien a faire

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_handledatafordtable;
--/
CREATE FUNCTION sp_t_res_prod_controlables_handledatafordtable (p_idvp bigint, p_newserialno integer, p_newsuppresspl smallint, p_old_bemerk2 brasiltype_bemerk, p_new_bemerk2 brasiltype_bemerk)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE

	w_oldStockSize INT;
	w_oldCurrThreshold INT;
	w_oldOccupiedCount INT;

	nbreSelectedLigne INT := 0;
BEGIN


	SELECT ctrs_stock_size, ctrs_curr_threshold, ctrs_occupied_count INTO w_oldStockSize, w_oldCurrThreshold, w_oldOccupiedCount
	FROM t_d_controlable_rscs WHERE rpct_id = p_idVp AND ctrs_role = 0;
	
	-- Le VP est gere pour la recherche de ressource
	GET DIAGNOSTICS nbreSelectedLigne = ROW_COUNT;
	IF (nbreSelectedLigne != 0) THEN
		

		PERFORM brasil_checkAfterUpdateResource(p_idVp, p_newSerialNo, p_newSuppressPl, p_old_bemerk2, p_new_bemerk2, w_oldStockSize, w_oldCurrThreshold, w_oldOccupiedCount);

	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_handledatafordtableil;
--/
CREATE FUNCTION sp_t_res_prod_controlables_handledatafordtableil (p_idil bigint, p_newserialno integer, p_newsuppresspl smallint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_oldOccupiedCount INT;
	nbreSelectedLigne INT := 0;
	curr_threshold INT;
BEGIN
	SELECT ctrs_occupied_count INTO w_oldOccupiedCount
		FROM t_d_controlable_rscs
		WHERE rpct_id = p_idIL;

	GET DIAGNOSTICS nbreSelectedLigne = ROW_COUNT;
	-- L'interface est gere pour la recherche de ressource
	IF (nbreSelectedLigne != 0) THEN

		IF (p_newSuppressPl = 1 AND w_oldOccupiedCount > p_newSerialNo) THEN
			PERFORM brasil_raiseException(11, '6');
		ELSE
			IF (p_newSuppressPl = 1) THEN
				curr_threshold := p_newSerialNo;
			ELSE
				curr_threshold := 1000000;
			END IF;
			
			UPDATE	t_d_controlable_rscs
			SET		ctrs_curr_threshold = curr_threshold
			WHERE	rpct_id = p_idIL;
		END IF;


	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_ins;
--/
CREATE FUNCTION sp_t_res_prod_controlables_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	oldAddInfoA BrasilType_AddInfo;
	newAddInfoA BrasilType_AddInfo;
	listeAddInfo BrasilType_AddInfo[2];

	oldAddInfoB BrasilType_AddInfo;
	newAddInfoB BrasilType_AddInfo;
BEGIN
	
	newAddInfoA.port_id := new.a_port_id;
	newAddInfoA.pogr_id := new.a_pogr_id;
	newAddInfoA.typeExtPhys := new.rpct_point_a_phys_end_type;
	newAddInfoA.typeInterface := new.rpct_type;
	newAddInfoA.interfaceId := new.rpct_point_a_interface_id;
	
	
	newAddInfoB.port_id := new.b_port_id;
	newAddInfoB.pogr_id := new.b_pogr_id;
	newAddInfoB.typeExtPhys := new.rpct_point_b_phys_end_type;
	newAddInfoB.typeInterface := new.rpct_point_b_interface_type;
	newAddInfoB.interfaceId := new.rpct_point_b_interface_id;
	newAddInfoB.ce_eqpt_id := new.ce_eqpt_id;
	newAddInfoB.ce_shelf_num := new.rpct_point_b_ce_shelf_num;
	newAddInfoB.ce_card_num := new.rpct_point_b_ce_card_num;
	newAddInfoB.ce_port_num := new.rpct_point_b_ce_port_num;
	
	PERFORM brasil_updateAllocableVc_lockedRange(new.rpct_id);
	
	CASE
	-- Cas d'une interface
	WHEN (new.rpct_type = 'I') THEN
		PERFORM sp_t_res_prod_controlables_ptsExtInterface(oldAddInfoA, newAddInfoA);

	-- Cas d'un VLAN
	WHEN (new.rpct_type = 'W') THEN
		PERFORM sp_t_res_prod_controlables_ptsExtInterface(oldAddInfoA, newAddInfoA);
		PERFORM sp_t_res_prod_controlables_rank(oldAddInfoA , newAddInfoA);

	-- Cas d'un VP
	-- Mise a jour table brasilD pour les VP qui sont crees pour etre occupe au niveau VP
	WHEN (new.rpct_type='V') THEN
		 
		PERFORM sp_t_res_prod_controlables_ptsExtVP(oldAddInfoA, newAddInfoA, oldAddInfoB, newAddInfoB);
		
		PERFORM sp_t_res_prod_controlables_updateBrasilDCtrlRscReserveVP(0::BIGINT, new.rpct_id, '', new.rpct_type, 0::BIGINT, new.a_eqpt_id, '', new.rpct_point_a_interface_id);
	ELSE
		-- ne rien faire
	END CASE;
	
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_mutationvlan;
--/
CREATE FUNCTION sp_t_res_prod_controlables_mutationvlan (p_new_rpct_id bigint, p_oldvorgang character, p_newvorgang character)  RETURNS void
  VOLATILE
AS $dbvis$
--(p_oldDataBearbTel CHAR(24), p_newDataBearbTel CHAR(24), p_oldVorgang CHAR(80), p_newVorgang CHAR(80)) RETURNING CHAR(24), CHAR(80)
DECLARE
    -- Les elements qui peuvent etre modifie
    w_idNewEqA BIGINT;
    w_idNewNodeA BIGINT;
    w_newExtA BrasilType_AddInfo;
    --DEFINE w_newExtAVlanInterneConcat CHAR(24);

    -- Les infos de la TC et de la TCVers
    w_idTC BIGINT;
    w_oldExtA BrasilType_AddInfo;
    w_idOldEqA BIGINT;

BEGIN

	--LET w_idNewEqA = DECODE(p_newVorgang[4], ' ', 0, p_newVorgang[4,11]::INT);
	w_idNewEqA := CASE WHEN SUBSTRING(p_newVorgang FROM 4 FOR 1)  = ' ' THEN 0 ELSE TRIM(SUBSTRING(p_newVorgang FROM 4 FOR 8))::BIGINT END;
	--LET w_idNewNodeA = DECODE(p_newVorgang[13], ' ', 0, p_newVorgang[13,22]::INT);
	w_idNewNodeA := CASE WHEN SUBSTRING(p_newVorgang FROM 13 FOR 1) = ' ' THEN 0 ELSE TRIM(SUBSTRING(p_newVorgang FROM 13 FOR 10))::BIGINT END;
	
	--w_newExtA := p_newVorgang[24,41];
	IF(SUBSTRING(p_newVorgang FROM 24 FOR 1) != ' ') THEN
		w_newExtA.typeInterface := SUBSTRING(p_newVorgang FROM 37 FOR 1);
		IF (w_newExtA.typeInterface = 'P') THEN
			w_newExtA.port_id := TRIM(SUBSTRING(p_newVorgang FROM 24 FOR 9))::BIGINT;
		ELSIF (w_newExtA.typeInterface = 'G') THEN
			SELECT gr.pogr_id FROM t_port_groups gr JOIN t_ports p ON gr.pogr_id = p.pogr_id INTO w_newExtA.pogr_id 
			WHERE p.card_id = TRIM(SUBSTRING(p_newVorgang FROM 24 FOR 9))::BIGINT AND gr.pogr_name = TRIM(SUBSTRING(p_newVorgang FROM 34 FOR 3));
		END IF;
		w_newExtA.typeExtPhys := SUBSTRING(p_newVorgang FROM 33 FOR 1);
		
		w_newExtA.interfaceId := TRIM(SUBSTRING(p_newVorgang FROM 38 FOR 4));
	END IF;
	

    IF (p_oldVorgang = '') THEN

        IF (p_newVorgang != '') THEN


            -- Recuperation des infos de la TC et de la TCVers
            /*SELECT    X1077_43_respondMO, X1588_102_mychars
            INTO    w_idTC, w_oldExtA
            FROM    TCVers
            WHERE    id = w_idTCVers;*/
            
            SELECT	rpct_id, 
			a_port_id, rpct_point_a_phys_end_type, a_pogr_id, a_eqpt_id
			INTO	w_idTC, w_oldExtA.port_id, w_oldExtA.typeExtPhys, w_oldExtA.pogr_id, w_idOldEqA
			FROM	t_res_prod_controlables
			WHERE	rpct_id = p_new_rpct_id;

			-- Au cas ou Ironman ferait un insert/update
			IF ((NOT(w_newExtA IS NULL) AND w_oldExtA != w_newExtA) OR (NOT(w_newExtB IS NULL) AND w_oldExtB != w_newExtB)) THEN
				-- Le pointA a ete modifie
				IF (NOT(w_newExtA IS NULL)) THEN

                       PERFORM sp_t_res_prod_controlables_ChekAndUpdateExt(w_newExtA, w_oldExtA);

                        --LET w_idNewNodeCA = brasil_ExternContPers_getNodeC(w_idNewNodeA);

                END IF;

                -- Mise a jour de la TC et de la TCVers

                -- On ne modifie la TC que si le noeud a change
                -- classId a -1 pour que le trigger laisse passer la modif
                /*IF (w_idNewNodeA != 0) THEN
                    UPDATE    TC
                    SET       X1563_1_cmNode = DECODE(w_idNewNodeA, 0, X1563_1_cmNode, w_idNewNodeA),
                              X1563_3_cmNode = DECODE(w_idNewNodeA, 0, X1563_1_cmNode, w_idNewNodeA),
			      classId = -1
                    WHERE     id = w_idTC
                    ;
                END IF;*/

                --LET w_newExtAVlanInterneConcat = w_newExtA||w_oldExtA[44,49];	

                -- Dans tous les cas, on modifie la TCVers
                -- X1588_87_cmFarEndA = -1 pour que le trigger laisse passer la modif concernant les nodeC
                -- X1588_93_cmPath = -1 pour que le trigger laisse passer la modif des equipement extremite
                -- classId = -1 pour que le trigger laisse passer la modif des extremites
                /* YIR: Cette MAJ n'est plus necessaire*/
				/*UPDATE    TCVers
                SET     X1588_88_cmFarEndA = DECODE(w_idNewNodeCA, 0, X1588_88_cmFarEndA, w_idNewNodeCA),
			X1588_90_cmFarEndB = DECODE(w_idNewNodeCA, 0, X1588_88_cmFarEndA, w_idNewNodeCA),
                        X1588_87_cmFarEndA = -1,
                        X1588_69_mychars = DECODE(w_idNewEqA, 0, X1588_69_mychars, RPAD(w_idNewEqA, 13, ' ')),
                        X1588_93_cmPath = DECODE(w_idNewEqA, 0, 0, -1),
                        X1588_102_mychars = DECODE(w_newExtA[1], ' ', X1588_102_mychars, RPAD(w_newExtAVlanInterneConcat, 160, ' ')),
                        classId = -1
                WHERE    id = w_idTCVers
                ;*/


                -- Mise a jour de la table brasilD_controlableRsc si besoin (modif vpiA, eqA, eqB ou portA)
                IF (NOT(w_newExtA IS NULL) OR w_idNewEqA != 0) THEN
                    /*UPDATE    brasilD_controlableRsc
                    SET        logicalEqA = DECODE(w_idNewEqA, 0, logicalEqA, w_idNewEqA),
                            portA = DECODE(w_newExtA[1], ' ', portA, DECODE(w_newExtA[10], 'P', w_newExtA[1,9]::INT, 0)),
                            vpiA = DECODE(w_newExtA[1], ' ', vpiA, w_newExtA[15,18]::INT)
                    WHERE    id = w_idTC;
                    */
					
					UPDATE t_d_controlable_rscs
					SET a_eqpt_id = CASE WHEN w_idNewEqA = 0 THEN a_eqpt_id ELSE w_idNewEqA END,
					a_port_id = CASE WHEN w_newExtA.typeExtPhys = 'P' AND w_newExtA.port_id IS NOT NULL THEN w_newExtA.port_id ELSE a_port_id END,
					ctrs_vpia = CASE WHEN w_newExtA.interfaceId IS NOT NULL THEN w_newExtA.interfaceId ELSE ctrs_vpia END
					WHERE rpct_id = w_idTC;
                END IF;

            END IF;

        END IF;

    END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_mutationvp;
--/
CREATE FUNCTION sp_t_res_prod_controlables_mutationvp (p_new_rpct_id bigint, p_oldvorgang character, p_newvorgang character, w_oldexta brasiltype_addinfo, w_oldextb brasiltype_addinfo, w_idoldeqa bigint, w_idoldeqb bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	-- Les elements qui peuvent etre modifie
	w_idNewEqA BIGINT;
	w_idNewNodeA BIGINT;
	w_newExtA BrasilType_AddInfo;
	w_idNewEqB BIGINT;
	w_idNewNodeB BIGINT;
	w_newExtB BrasilType_AddInfo;

	-- nb utilisateur ExtA
	--w_nbUtilA INT;
	--w_nbUtilAA1 INT;
	--w_nbUtilAA2 INT;
	--w_nbUtilAB2 INT;

	-- nb utilisateur ExtB
	w_nbUtilB INT;
	w_nbUtilBA1 INT;
	w_nbUtilBA2 INT;
	w_nbUtilBB2 INT;

	-- Pour comparaison en utilisant l'index
	--DEFINE w_extAComp CHAR(15);
	--DEFINE w_extBComp CHAR(15);

	-- Les infos de la TC et de la TCVers
	w_typeExtPhysB CHAR(1);

	w_interfaceId CHAR(39);
BEGIN

	--LET w_idNewEqA = DECODE(p_newVorgang[4], ' ', 0, p_newVorgang[4,11]::INT);
	w_idNewEqA := CASE WHEN SUBSTRING(p_newVorgang FROM 4 FOR 1)  = ' ' THEN 0 ELSE TRIM(SUBSTRING(p_newVorgang FROM 4 FOR 8))::BIGINT END;
	--LET w_idNewNodeA = DECODE(p_newVorgang[13], ' ', 0, p_newVorgang[13,22]::INT);
	w_idNewNodeA := CASE WHEN SUBSTRING(p_newVorgang FROM 13 FOR 1) = ' ' THEN 0 ELSE TRIM(SUBSTRING(p_newVorgang FROM 13 FOR 10))::BIGINT END;
	
	--w_newExtA := p_newVorgang[24,41];
	IF(SUBSTRING(p_newVorgang FROM 24 FOR 1) != ' ') THEN
		w_newExtA.typeExtPhys := SUBSTRING(p_newVorgang FROM 33 FOR 1);
		w_newExtA.typeInterface := SUBSTRING(p_newVorgang FROM 37 FOR 1);
		IF (w_newExtA.typeExtPhys = 'P') THEN
			w_newExtA.port_id := TRIM(SUBSTRING(p_newVorgang FROM 24 FOR 9))::BIGINT;
		ELSIF (w_newExtA.typeExtPhys = 'G') THEN
			SELECT gr.pogr_id FROM t_port_groups gr JOIN t_ports p ON gr.pogr_id = p.pogr_id INTO w_newExtA.pogr_id 
			WHERE p.card_id = TRIM(SUBSTRING(p_newVorgang FROM 24 FOR 9))::BIGINT AND gr.pogr_name = TRIM(SUBSTRING(p_newVorgang FROM 34 FOR 3));
		END IF;
		w_newExtA.interfaceId := TRIM(SUBSTRING(p_newVorgang FROM 38 FOR 4));
	END IF;
	
	--LET w_idNewEqB = DECODE(p_newVorgang[43], ' ', 0, p_newVorgang[43,50]::INT);
	w_idNewEqB := CASE WHEN SUBSTRING(p_newVorgang FROM 43 FOR 1) = ' ' THEN 0 ELSE TRIM(SUBSTRING(p_newVorgang FROM 43 FOR 8))::BIGINT END;
	--LET w_idNewNodeB = DECODE(p_newVorgang[52], ' ', 0, p_newVorgang[52,61]::INT);
	w_idNewNodeB := CASE WHEN SUBSTRING(p_newVorgang FROM 52 FOR 1) = ' ' THEN 0 ELSE TRIM(SUBSTRING(p_newVorgang FROM 52 FOR 10))::BIGINT END;

	IF(SUBSTRING(p_newVorgang FROM 63 FOR 1) != ' ') THEN
		w_typeExtPhysB := SUBSTRING(p_newVorgang FROM 72 FOR 1);
		IF (w_typeExtPhysB = 'P') THEN
			w_newExtB.port_id := TRIM(SUBSTRING(p_newVorgang FROM 63 FOR 9))::INT;
			w_newExtB.typeExtPhys := SUBSTRING(p_newVorgang FROM 72 FOR 1);
			w_newExtB.typeInterface := SUBSTRING(p_newVorgang FROM 76 FOR 1);
			w_newExtB.interfaceId := TRIM(SUBSTRING(p_newVorgang FROM 77 FOR 4));
		ELSIF ( w_typeExtPhysB = 'N') THEN
			w_newExtB.ce_eqpt_id := TRIM(SUBSTRING(p_newVorgang FROM 63 FOR 8))::INT;
			w_newExtB.typeExtPhys := SUBSTRING(p_newVorgang FROM 72 FOR 1);
			w_newExtB.ce_shelf_num := TRIM(SUBSTRING(p_newVorgang FROM 73 FOR 2))::SMALLINT;
			w_newExtB.ce_card_num := TRIM(SUBSTRING(p_newVorgang FROM 75 FOR 2))::SMALLINT;
			w_newExtB.ce_port_num := TRIM(SUBSTRING(p_newVorgang FROM 77 FOR 3))::SMALLINT;
			w_newExtB.typeInterface := p_newVorgang[80];
			
		ELSIF ( w_typeExtPhysB = 'G') THEN
			SELECT gr.pogr_id FROM t_port_groups gr JOIN t_ports p ON gr.pogr_id = p.pogr_id INTO w_newExtB.pogr_id 
			WHERE p.card_id = TRIM(SUBSTRING(p_newVorgang FROM 63 FOR 9))::BIGINT AND gr.pogr_name = TRIM(SUBSTRING(p_newVorgang FROM 73 FOR 3));
			w_newExtB.typeExtPhys := SUBSTRING(p_newVorgang FROM 72 FOR 1);
			w_newExtB.typeInterface := SUBSTRING(p_newVorgang FROM 76 FOR 1);
			w_newExtB.interfaceId := TRIM(SUBSTRING(p_newVorgang FROM 77 FOR 4));
		END IF;
	END IF;
			
			
	IF (p_oldVorgang = '') THEN

		IF (p_newVorgang != '') THEN



			-- Si les 2 sont modifies, et qu'ils sont egaux, on leve une exception
			IF (NOT(w_newExtA IS NULL) AND w_newExtA IS NOT DISTINCT FROM w_newExtB) THEN
				PERFORM brasil_raiseException(11, '83');
			END IF;

			-- Au cas ou Ironman ferait un insert/update
			IF ((NOT(w_newExtA IS NULL) AND w_oldExtA != w_newExtA) OR (NOT(w_newExtB IS NULL) AND w_oldExtB != w_newExtB)) THEN
				-- Le pointA a ete modifie
				IF (NOT(w_newExtA IS NULL)) THEN

						-- Verification de l'utilisation de la nouvelle extA
						-- L'extA peut être utilisee par un lien support ou par un VP avec un interfaceId different ou par autre interface

						-- Nb d'utilisateur de extA en ExtA, avec type = D (=0)
						/*LET w_extAComp = w_newExtA[1,13]||"D%";
						SELECT COUNT(*) INTO w_nbUtilAA1 FROM TCVers WHERE
							X1588_102_mychars LIKE w_extAComp;*/
							
						-- Nb d'utilisateur de extA en ExtA, V et interfaceId egale (=0)
						/*SELECT COUNT(*) INTO w_nbUtilAA2 FROM TCVers WHERE
							X1588_102_mychars = w_newExtA;*/
							
						-- Nb d'utilisateur de extA en ExtB, V et interfaceId egale (=0)
						/*SELECT COUNT(*) INTO w_nbUtilAB2 FROM TCVers WHERE
							X1588_55_mychars = w_newExtA;*/

					
						PERFORM sp_t_res_prod_controlables_ChekAndUpdateExt(w_newExtA, w_oldExtA);


						--w_idNewNodeCA := w_idNewNodeA;--brasil_ExternContPers_getNodeC(w_idNewNodeA);

				END IF;





				-- Le pointB a ete modifie
				IF (NOT(w_newExtB IS NULL)) THEN

					-- Verification de l'utilisation de la nouvelle extB
					-- L'extB peut être utilisee par un lien support ou par un VP avec un interfaceId different ou par autre interface
					IF (w_newExtB.typeExtPhys='N') THEN

						-- Recuperation de l'interface id, si l'extA est modifiee, on recupere le nouvel interfaceId sinon, on prend l'ancien
						IF (w_newExtA.interfaceId != '') THEN
							w_interfaceId = w_newExtA.interfaceId;
						ELSE
							w_interfaceId = w_oldExtA.interfaceId;
						END IF;

						-- Nb d'utilisateur de extB en ExtB, V et interfaceId egale (=1)
						-- Test interfaceId sur ExtA
						/*SELECT COUNT(*) INTO w_nbUtilBB2 FROM TCVers WHERE
							X1588_55_mychars = w_newExtB
							AND X1588_102_mychars[15,18] = w_interfaceId;*/
							
						SELECT COUNT(*) FROM t_res_prod_controlables INTO w_nbUtilB WHERE
						b_pogr_id = CASE WHEN p_new_Ext.typeExtPhys = 'P' THEN b_pogr_id ELSE p_new_Ext.pogr_id END
						AND b_port_id = CASE WHEN p_new_Ext.typeExtPhys = 'G' THEN b_port_id ELSE p_new_Ext.port_id END
						AND rpct_point_b_phys_end_type = p_new_Ext.typeExtPhys
						AND rpct_point_b_interface_type = p_new_Ext.typeInterface
						AND rpct_point_b_interface_id = CASE WHEN w_interfaceId IS NOT NULL THEN w_interfaceId ELSE rpct_point_b_interface_id END  ;

						--w_nbUtilB := w_nbUtilBB2;
						IF (w_nbUtilB != 0) THEN
							PERFORM brasil_raiseException(11, '64');
						END IF;
					ELSE

						-- Nb d'utilisateur de extB en ExtA, type = D (=0)
						/*LET w_extBComp = w_newExtB[1,13]||"D%";
						SELECT COUNT(*) INTO w_nbUtilBA1 FROM TCVers WHERE
							X1588_102_mychars LIKE w_extBComp;*/

						-- Nb d'utilisateur de extB en ExtA, V et interfaceId egale (=0)
						/*SELECT COUNT(*) INTO w_nbUtilBA2 FROM TCVers WHERE
							X1588_102_mychars = w_newExtB;*/

						-- Nb d'utilisateur de extB en ExtB, V et interfaceId egale (=1)
						/*SELECT COUNT(*) INTO w_nbUtilBB2 FROM TCVers WHERE
							X1588_55_mychars = w_newExtB;

						LET w_nbUtilB = w_nbUtilBA1 + w_nbUtilBA2 + w_nbUtilBB2;*/
						
						PERFORM sp_t_res_prod_controlables_ChekAndUpdateExt(w_newExtB, w_oldExtB);

					END IF;

					--LET w_idNewNodeCB := w_idNewNodeB;--brasil_ExternContPers_getNodeC(w_idNewNodeB);


					-- Changement d'equipement logique B (propagation modification du NIP sur MRTAccesService et sur RessourcePourDslamTstF)
					IF (w_idNewEqB != 0) THEN

						-- Mise a jour des TCVers occupante (MRTAccesService) via AssResRel et ayant le outServPlOrderId = w_idOldEqB
						/*UPDATE	TCVers
						SET 	X1588_70_mychars = RPAD(w_idNewEqB, 13, ' '),
								updateCounter = updateCounter + 1
						WHERE	id IN (
									SELECT	X1569_1_cmAssembly
									FROM	AssResRel
									WHERE	X1569_3_cmResource = w_idTC
								)
							AND	X1588_70_mychars = w_idOldEqB
						;*/

						-- Mise a jour des TCVers occupante (MRTAccesService) via AssResRel et ayant le outServPlOrderId = w_idOldEqB
						UPDATE	t_mrt_access_services
						SET 	eqpt_id = w_idNewEqB
						WHERE	mras_id IN (
							SELECT	mras_id
							FROM	t_resource_usages
							WHERE	rpct_id = p_new_rpct_id)
						AND	eqpt_id = w_idOldEqB;
						
						-- Mise a jour des MSPEntry (RessourcePourDslamTstF) ayant moVersion = w_idTCVers et versId = w_idOldEqB
						/*UPDATE	MSPEntry
						SET		X1095_1_intval = w_idNewEqB,
								updateCounter = updateCounter + 1
						WHERE	X1095_9_mMoVersion = w_idTCVers
							AND	X1095_1_intval = w_idOldEqB
						;*/

						-- Mise a jour des MSPEntry (RessourcePourDslamTstF) ayant moVersion = w_idTCVers et versId = w_idOldEqB
						UPDATE t_res_prod_roles 
						SET  nip_eqpt_id = w_idNewEqB 
						WHERE rpct_id = p_new_rpct_id
						AND nip_eqpt_id = w_idOldEqB;
						

					END IF;

				END IF;



				-- Mise a jour de la TC et de la TCVers

				-- On ne modifie la TC que si un des 2 noeuds a change
				-- classId a -1 pour que le trigger laisse passer la modif
				/*IF (w_idNewNodeA != 0 OR w_idNewNodeB != 0) THEN
					UPDATE	TC
					SET		X1563_1_cmNode = DECODE(w_idNewNodeA, 0, X1563_1_cmNode, w_idNewNodeA),
							X1563_3_cmNode = DECODE(w_idNewNodeB, 0, X1563_3_cmNode, w_idNewNodeB),
							classId = -1
					WHERE 	id = w_idTC
					;
				END IF;*/

				-- Dans tous les cas, on modifie la TCVers
				-- X1588_87_cmFarEndA = -1 pour que le trigger laisse passer la modif concernant les nodeC
				-- X1588_93_cmPath = -1 pour que le trigger laisse passer la modif des equipement extremite
				-- classId = -1 pour que le trigger laisse passer la modif des extremites
				
				/* YIR: Cette MAJ n'est plus necessaire*/
				/*UPDATE	TCVers
				SET		X1588_88_cmFarEndA = DECODE(w_idNewNodeCA, 0, X1588_88_cmFarEndA, w_idNewNodeCA),
						X1588_90_cmFarEndB = DECODE(w_idNewNodeCB, 0, X1588_90_cmFarEndB, w_idNewNodeCB),
						X1588_87_cmFarEndA = -1,
						X1588_69_mychars = DECODE(w_idNewEqA, 0, X1588_69_mychars, RPAD(w_idNewEqA, 13, ' ')),
						X1588_70_mychars = DECODE(w_idNewEqB, 0, X1588_70_mychars, RPAD(w_idNewEqB, 13, ' ')),
						X1588_93_cmPath = DECODE(w_idNewEqA, 0, DECODE(w_idNewEqB, 0, X1588_93_cmPath, -1), -1),
						X1588_102_mychars = DECODE(w_newExtA[1], ' ', X1588_102_mychars, RPAD(w_newExtA, 160, ' ')),
						X1588_55_mychars = DECODE(w_newExtB[1], ' ', X1588_55_mychars, RPAD(w_newExtB, 20, ' ')),
						classId = -1
				WHERE	id = w_idTCVers
				;*/


				-- Mise a jour de la table brasilD_controlableRsc si besoin (modif vpiA, eqA, eqB ou portA)
				IF (NOT(w_newExtA IS NULL) OR w_idNewEqA != 0 OR w_idNewEqB != 0) THEN
					/*UPDATE	brasilD_controlableRsc
					SET		logicalEqA = DECODE(w_idNewEqA, 0, logicalEqA, w_idNewEqA),
							portA = DECODE(w_newExtA[1], ' ', portA, DECODE(w_newExtA[10], 'P', w_newExtA[1,9]::INT, 0)),
							vpiA = DECODE(w_newExtA[1], ' ', vpiA, w_newExtA[15,18]::INT),
							logicalEqB = DECODE(w_idNewEqB, 0, logicalEqB, w_idNewEqB)
					WHERE	id = w_idTC;*/
					
					UPDATE t_d_controlable_rscs
					SET a_eqpt_id = CASE WHEN w_idNewEqA = 0 THEN a_eqpt_id ELSE w_idNewEqA END,
					a_port_id = CASE WHEN w_newExtA.typeExtPhys = 'P' AND w_newExtA.port_id IS NOT NULL THEN w_newExtA.port_id ELSE a_port_id END,
					ctrs_vpia = CASE WHEN w_newExtA.interfaceId IS NOT NULL THEN w_newExtA.interfaceId::INT ELSE ctrs_vpia END,
					b_eqpt_id = CASE WHEN w_idNewEqB = 0 THEN b_eqpt_id ELSE w_idNewEqB END
					WHERE rpct_id = p_new_rpct_id;
				END IF;

			END IF;

		END IF;

	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_ptsextinterface;
--/
CREATE FUNCTION sp_t_res_prod_controlables_ptsextinterface (p_oldaddinfo brasiltype_addinfo, p_newaddinfo brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nbUtil INT := 0;
	w_nbUtilAA1 INT := 0;
	w_nbUtilAA2 INT := 0;

BEGIN
	IF (p_newAddInfo.typeInterface IN ('W', 'I') AND NOT(p_newAddInfo IS NULL)) THEN
		IF (p_oldAddInfo.typeInterface = '' OR p_oldAddInfo IS NULL) THEN


			-- L'extA peut être utilisee par un lien support ou par le même type d'interface avec interfaceId different ou par autre interface

			-- Nb d'utilisateur de ExtA en extA, avec typeInterface = D(=0)
			-- On autorise L, V, W et I
			IF (p_newAddInfo.typeExtPhys = 'P') THEN
				SELECT COUNT(*) INTO w_nbUtilAA1 FROM t_mrt_access_dslams 
				WHERE a_port_id = p_newAddInfo.port_id AND mrtd_point_a_phys_end_type = 'P';
				
				-- Nb d'utilisateur de ExtA en extA, avec typeInterface et interfaceId egaux (=1)
				SELECT COUNT(*) INTO w_nbUtilAA2 FROM t_res_prod_controlables 
				WHERE a_port_id  = p_newAddInfo.port_id 
				AND  rpct_point_a_interface_type = p_newAddInfo.typeInterface 
				AND rpct_point_a_interface_id = p_newAddInfo.interfaceId
				AND rpct_point_a_phys_end_type = 'P';
				
			ELSIF (p_newAddInfo.typeExtPhys = 'G') THEN
				-- Nb d'utilisateur de extA en ExtA, avec type = D (=0) en cas d'extremite groupe de port reel
				SELECT COUNT(*) INTO w_nbUtilAA1 FROM t_mrt_access_dslams 
				WHERE a_pogr_id = p_newAddInfo.pogr_id  AND mrtd_interface_type = 'D';
				
				-- Nb d'utilisateur de ExtA en extA, avec typeInterface et interfaceId egaux (=1)
				SELECT COUNT(*) INTO w_nbUtilAA2 FROM t_res_prod_controlables 
				WHERE a_pogr_id = p_newAddInfo.pogr_id
				AND  rpct_point_a_interface_type = p_newAddInfo.typeInterface 
				AND rpct_point_a_interface_id = p_newAddInfo.interfaceId
				AND rpct_point_a_phys_end_type = 'G';
			END IF;


			-- Nb d'utilisateur de ExtA en extB, autre que L (=0)
			-- On autorise L et V donc plus de raison de verifier

			w_nbUtil := w_nbUtilAA1 + w_nbUtilAA2;

			IF (w_nbUtil!=1) THEN
				PERFORM brasil_raiseException(11, '64');
			END IF;

			-- ExtA=ExtPort
			IF (p_newAddInfo.typeExtPhys = 'P') THEN
				PERFORM sp_checkAndUpdateNewP(p_newAddInfo.port_id, 1);

			-- ExtA=ExtGroupe
			ELSE
				PERFORM sp_checkAndUpdateNewG(p_newAddInfo.pogr_id, 1);
			END IF;
		END IF;
	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_ptsextvlan;
--/
CREATE FUNCTION sp_t_res_prod_controlables_ptsextvlan (p_oldaddinfo brasiltype_addinfo, p_newaddinfo brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	-- nb utilisateur ExtA
	w_nbUtilA INT := 0;
	w_nbUtilAA1 INT := 0;
	w_nbUtilAA2 INT := 0;

BEGIN

	--RAISE NOTICE '------------------ p_oldAddInfo.typeInterface = <%> p_newAddInfo.typeInterface <%>',p_oldAddInfo.typeInterface,p_newAddInfo.typeInterface;
	IF (p_newAddInfo.typeInterface  = 'W' AND p_newAddInfo.typeInterface IS NOT NULL) THEN
		IF (p_oldAddInfo.typeInterface IS NULL) THEN


			-- L'extA et l'extB peuvent être utilisees par un lien support ou par un VLAN avec un interfaceId different ou par autre interface

			IF (p_newAddInfo.typeExtPhys = 'P') THEN
				-- Nb d'utilisateur de extA en ExtA, avec type = D (=0)
				SELECT COUNT(*) INTO w_nbUtilAA1 FROM t_mrt_access_dslams 
				WHERE a_port_id = p_newAddInfo.port_id AND mrtd_point_a_phys_end_type = 'P' AND mrtd_interface_type = 'D';
				
				-- Nb d'utilisateur de extA en ExtA, W et interfaceId egale (=1)
				SELECT COUNT(*) INTO w_nbUtilAA2 FROM t_res_prod_controlables 
				WHERE a_port_id  = p_newAddInfo.port_id 
				AND  rpct_point_a_interface_type = p_newAddInfo.typeInterface 
				AND rpct_point_a_interface_id = p_newAddInfo.interfaceId
				AND rpct_point_a_phys_end_type = 'P';
				
			ELSIF (p_newAddInfo.typeExtPhys = 'G') THEN
				-- Nb d'utilisateur de extA en ExtA, avec type = D (=0)
				SELECT COUNT(*) INTO w_nbUtilAA1 FROM t_mrt_access_dslams 
				WHERE a_pogr_id = p_newAddInfo.pogr_id  AND mrtd_interface_type = 'D';
				
				-- Nb d'utilisateur de extA en ExtA, W et interfaceId egale (=1)
				SELECT COUNT(*) INTO w_nbUtilAA2 FROM t_res_prod_controlables 
				WHERE a_pogr_id = p_newAddInfo.pogr_id 
				AND  rpct_point_a_interface_type = p_newAddInfo.typeInterface 
				AND rpct_point_a_interface_id = p_newAddInfo.interfaceId
				AND rpct_point_a_phys_end_type = 'G';
			END IF;
			

			w_nbUtilA = w_nbUtilAA1 + w_nbUtilAA2;

			IF (w_nbUtilA != 1) THEN
				PERFORM brasil_raiseException(11, '64');
			END IF;

			-- ExtA=ExtPort
			IF (p_newAddInfo.typeExtPhys = 'P') THEN
				PERFORM sp_checkAndUpdateNewP(p_newAddInfo.port_id, 1);

			-- ExtA=ExtGroupe
			ELSE
				PERFORM sp_checkAndUpdateNewG(p_newAddInfo.pogr_id, 1);
			END IF;

		END IF;
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_ptsextvp;
--/
CREATE FUNCTION sp_t_res_prod_controlables_ptsextvp (p_oldaddinfo brasiltype_addinfo, p_newaddinfo brasiltype_addinfo, p_oldbpartner brasiltype_addinfo, p_newbpartner brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	-- nb utilisateur ExtA
	w_nbUtilA INT;
	-- nb utilisateur ExtB
	w_nbUtilB INT;

BEGIN

	IF (p_newAddInfo.typeInterface  = 'V' AND (p_newAddInfo.port_id IS NOT NULL OR p_newAddInfo.pogr_id IS NOT NULL)) THEN
		IF (p_oldAddInfo.typeInterface = '' OR p_oldAddInfo IS NULL) THEN

			w_nbUtilA := f_t_res_prod_controlables_getNbUtil(p_newAddInfo);

			IF (p_newBPartner.typeExtPhys='N') THEN

				-- Nb d'utilisateur de extB en ExtB, V et interfaceId egale (=1)
				-- Test interfaceId sur ExtA
				SELECT COUNT(*) INTO w_nbUtilB FROM t_res_prod_controlables 
						WHERE ce_eqpt_id = p_newBPartner.ce_eqpt_id  
						AND rpct_point_b_ce_shelf_num = p_newBPartner.ce_shelf_num 
						AND rpct_point_b_ce_card_num = p_newBPartner.ce_card_num 
						AND rpct_point_b_ce_port_num = p_newBPartner.ce_port_num
						AND rpct_point_b_phys_end_type = 'N'
						AND rpct_point_b_interface_type = p_newBPartner.typeInterface
						AND rpct_point_a_interface_id = p_newAddInfo.interfaceId;
				

			ELSE

				w_nbUtilB = f_t_res_prod_controlables_getNbUtil(p_newBPartner);

			END IF;

			IF ((w_nbUtilA + w_nbUtilB) != 2) THEN
				PERFORM brasil_raiseException(11, '64');
			END IF;

			-- ExtA=ExtPort
			IF (p_newAddInfo.typeExtPhys = 'P') THEN
				PERFORM sp_checkAndUpdateNewP(p_newAddInfo.port_id, 1);

			-- ExtA=ExtGroupe
			ELSE
				PERFORM sp_checkAndUpdateNewG(p_newAddInfo.pogr_id, 1);
			END IF;

			-- ExtB=ExtPort
			IF (p_newBPartner.typeExtPhys ='P') THEN
				PERFORM sp_checkAndUpdateNewP(p_newBPartner.port_id, 1);

			-- ExtB=ExtGroupe
			ELSIF (p_newBPartner.typeExtPhys = 'G') THEN
				PERFORM sp_checkAndUpdateNewG(p_newBPartner.pogr_id, 1);
			END IF;


		END IF;
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_rank;
--/
CREATE FUNCTION sp_t_res_prod_controlables_rank (p_oldaddinfo brasiltype_addinfo, p_newaddinfo brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_newTCnbOccup INT := 0;
	w_newRank smallint;
	w_newLinkId BIGINT;
	
	w_oldTCnbOccup INT := 0;
	w_oldRank smallint;
	w_oldLinkId BIGINT;
BEGIN

	IF(p_oldAddInfo IS NULL AND p_newAddInfo.port_id IS NOT NULL) THEN

		
		IF (p_newAddInfo.typeExtPhys = 'P') THEN
			SELECT COUNT(*) INTO w_newTCnbOccup FROM t_res_prod_controlables
			WHERE a_port_id = p_newAddInfo.port_id AND rpct_point_a_phys_end_type = p_newAddInfo.typeExtPhys AND rpct_type = p_newAddInfo.typeInterface;
		--ELSIF (p_newAddInfo.typeExtPhys = 'G') THEN
		--	SELECT COUNT(*) INTO w_newTCnbOccup FROM t_res_prod_controlables
		--	WHERE a_pogr_id = p_newAddInfo.pogr_id AND rpct_point_a_phys_end_type = p_newAddInfo.typeExtPhys 
		--	AND rpct_type = p_newAddInfo.typeInterface;
		--END IF;
		
			SELECT  mdlk_rank, mdlk_id INTO w_newRank, w_newLinkId FROM  t_media_links t
				WHERE a_port_id = p_newAddInfo.port_id AND mdlk_point_a_phys_end_type = p_newAddInfo.typeExtPhys;
	
			--IF (w_newTCnbOccup>0 AND w_newRank=0) THEN
			IF (w_newRank=0) THEN
				UPDATE t_media_links
				SET mdlk_rank = 1
				WHERE mdlk_id = w_newLinkId;
			END IF;
		END IF;

	ELSE
		IF(p_oldAddInfo.port_id IS NOT NULL AND p_newAddInfo IS NULL) THEN

			IF (p_oldAddInfo.typeExtPhys = 'P') THEN
				SELECT COUNT(*) INTO w_oldTCnbOccup FROM t_res_prod_controlables
				WHERE a_port_id = p_oldAddInfo.port_id AND rpct_point_a_phys_end_type = p_oldAddInfo.typeExtPhys AND rpct_type = p_oldAddInfo.typeInterface;
			--ELSIF (p_oldAddInfo.typeExtPhys = 'G') THEN
			--	SELECT COUNT(*) INTO w_oldTCnbOccup FROM t_res_prod_controlables
			--	WHERE a_pogr_id = p_oldAddInfo.pogr_id AND rpct_point_a_phys_end_type = p_oldAddInfo.typeExtPhys 
			--	AND rpct_type = p_oldAddInfo.typeInterface;
			--END IF;
			
				SELECT mdlk_rank, mdlk_id INTO w_oldRank, w_oldLinkId FROM  t_media_links t
				WHERE a_port_id = p_oldAddInfo.port_id AND mdlk_point_a_phys_end_type = p_oldAddInfo.typeExtPhys;
	
				--RAISE NOTICE '########## w_oldTCnbOccup <%> w_oldRank <%>',w_oldTCnbOccup,w_oldRank;
				IF (w_oldTCnbOccup=1 AND w_oldRank=1) THEN
				--IF (w_oldRank=1) THEN
					UPDATE t_media_links
					SET mdlk_rank = 0
					WHERE mdlk_id = w_oldLinkId;
				END IF;
			END IF;

		END IF;
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_upd_role;
--/
CREATE FUNCTION sp_t_res_prod_controlables_upd_role ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	IF (NEW.role_id != OLD.role_id AND NEW.rpct_type = 'W') THEN
			PERFORM sp_t_res_prod_controlables_updateRoleForDTable(NEW.rpct_id, NEW.role_id);
	END IF;
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_update;
--/
CREATE FUNCTION sp_t_res_prod_controlables_update ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	oldAddInfoA BrasilType_AddInfo;
	newAddInfoA BrasilType_AddInfo;
	retAddInfoA BrasilType_AddInfo;
	listeAddInfo BrasilType_AddInfo[2];	
	
	oldAddInfoB BrasilType_AddInfo;
	newAddInfoB BrasilType_AddInfo;
	
	oldBemerk BrasilType_Bemerk;
	newBemerk BrasilType_Bemerk;
	
	w_idOldEqA BIGINT;
	w_idOldEqB BIGINT;

BEGIN
	-- Modif extremite A ou extremite B
	oldAddInfoA.port_id := old.a_port_id;
	oldAddInfoA.pogr_id := old.a_pogr_id;
	oldAddInfoA.typeExtPhys := old.rpct_point_a_phys_end_type;
	oldAddInfoA.typeInterface := old.rpct_type;
	oldAddInfoA.interfaceId := old.rpct_point_a_interface_id;
	
	newAddInfoA.port_id := new.a_port_id;
	newAddInfoA.pogr_id := new.a_pogr_id;
	newAddInfoA.typeExtPhys := new.rpct_point_a_phys_end_type;
	newAddInfoA.typeInterface := new.rpct_type;
	newAddInfoA.interfaceId := new.rpct_point_a_interface_id;
	
	oldAddInfoB.port_id := old.b_port_id;
	oldAddInfoB.pogr_id := old.b_pogr_id;
	oldAddInfoB.typeExtPhys := old.rpct_point_b_phys_end_type;
	oldAddInfoB.typeInterface := old.rpct_point_b_interface_type;
	oldAddInfoB.interfaceId := old.rpct_point_b_interface_id;
	oldAddInfoB.ce_eqpt_id := old.ce_eqpt_id;
	oldAddInfoB.ce_shelf_num := old.rpct_point_b_ce_shelf_num;
	oldAddInfoB.ce_card_num := old.rpct_point_b_ce_card_num;
	oldAddInfoB.ce_port_num := old.rpct_point_b_ce_port_num;
	
	newAddInfoB.port_id := new.b_port_id;
	newAddInfoB.pogr_id := new.b_pogr_id;
	newAddInfoB.typeExtPhys := new.rpct_point_b_phys_end_type;
	newAddInfoB.typeInterface := new.rpct_point_b_interface_type;
	newAddInfoB.interfaceId := new.rpct_point_b_interface_id;
	newAddInfoB.ce_eqpt_id := new.ce_eqpt_id;
	newAddInfoB.ce_shelf_num := new.rpct_point_b_ce_shelf_num;
	newAddInfoB.ce_card_num := new.rpct_point_b_ce_card_num;
	newAddInfoB.ce_port_num := new.rpct_point_b_ce_port_num;
	
	newBemerk.allocated_vc_count := new.rpct_allocables_vc_count;
	newBemerk.nb_locked_ranges := new.rpct_nb_locked_ranges;
	
	IF (old.rpct_vc_max != new.rpct_vc_max OR old.rpct_vc_min != new.rpct_vc_min) THEN
		newBemerk := brasil_updateAllocableVc_lockedRange(new.rpct_id);
	END IF;
	
	newBemerk.vc_max := new.rpct_vc_max;
	newBemerk.vc_min := new.rpct_vc_min;
	
	oldBemerk.allocated_vc_count := old.rpct_allocables_vc_count;
	oldBemerk.nb_locked_ranges := old.rpct_nb_locked_ranges;
	oldBemerk.vc_max := old.rpct_vc_max;
	oldBemerk.vc_min := old.rpct_vc_min;
	
	w_idOldEqA = old.a_eqpt_id;
	w_idOldEqB = old.b_eqpt_id;
	
	CASE
	-- Cas d'une interface
	WHEN (new.rpct_type ='I') THEN
		PERFORM sp_t_res_prod_controlables_ptsExtInterface(oldAddInfoA, newAddInfoA);

	-- Cas d'un VLAN
	WHEN (new.rpct_type = 'W') THEN
		PERFORM sp_t_res_prod_controlables_ptsExtVLAN(oldAddInfoA, newAddInfoA);
		
		PERFORM sp_t_res_prod_controlables_rank(oldAddInfoA , newAddInfoA);

	-- Cas d'un VP
	WHEN (new.rpct_type='V') THEN
		PERFORM sp_t_res_prod_controlables_ptsExtVP(oldAddInfoA, newAddInfoA, oldAddInfoB, newAddInfoB);
		
		
		PERFORM sp_t_res_prod_controlables_updateBrasilDCtrlRscReserveVP(old.rpct_id, new.rpct_id, old.rpct_type, new.rpct_type, old.a_eqpt_id, new.a_eqpt_id, old.rpct_point_a_interface_id, new.rpct_point_a_interface_id);
	ELSE
		-- ne rien faire	
	END CASE;
	-- Modif equipement A ou equipement B

	/*IF (new.rpct_type IN ('W','I','V')) THEN
		EXECUTE PROCEDURE brasil_TCVers_checkEqsExt(old.rpct_type, new.rpct_type, old.a_eqpt_id, new.a_eqpt_id, old.b_eqpt_id, new.b_eqpt_id, old.X1588_93_cmPath, new.X1588_93_cmPath)
			INTO a_eqpt_id, b_eqpt_id, X1588_93_cmPath;
		--EXECUTE PROCEDURE brasil_TCVers_checkEqsExt(old.X1588_52_mychars, new.X1588_52_mychars, old.X1588_69_mychars, new.X1588_69_mychars, old.X1588_70_mychars, new.X1588_70_mychars, old.X1588_93_cmPath, new.X1588_93_cmPath)
			--INTO X1588_69_mychars, X1588_70_mychars, X1588_93_cmPath;
	END IF;*/
	-- Controle du seuil

	-- Cas d'un VP, la mise a jour de la table denormalisee n'est necesssaire que lors d'une vrai modification
	IF (new.rpct_type ='V' ) THEN
		IF(oldBemerk IS DISTINCT FROM newBemerk) THEN
			PERFORM sp_t_res_prod_controlables_handleDataForDTable(new.rpct_id, new.rpct_prod_thresold, new.rpct_thresold_control, oldBemerk, newBemerk);
		ELSIF (new.rpct_prod_thresold != old.rpct_prod_thresold OR new.rpct_thresold_control != old.rpct_thresold_control) THEN
			PERFORM sp_t_res_prod_controlables_handleDataForDTable(new.rpct_id, new.rpct_prod_thresold, new.rpct_thresold_control, newBemerk, newBemerk);
		END IF;
	-- Cas d'une interface logique, la mise a jour de la table denormalisee n'est necesssaire que lors d'une vrai modification
	ELSIF (new.rpct_type IN ('I','W') AND (new.rpct_prod_thresold != old.rpct_prod_thresold OR new.rpct_thresold_control != old.rpct_thresold_control)) THEN
		PERFORM sp_t_res_prod_controlables_handleDataForDTableIL(new.rpct_id, new.rpct_prod_thresold, new.rpct_thresold_control);

	END IF;
	-- Modif disjflag

	-- Cas d'une RPC, la mise a jour de la table denormalisee n'est necesssaire que lors d'une vrai modification
	IF (new.rpct_type IN ('V','I','W') AND new.rpct_prod_status != old.rpct_prod_status) THEN
		PERFORM sp_t_res_prod_controlables_updateProdStateForDTable(new.rpct_id, new.rpct_prod_status);
	END IF;

	-- Modif noeudA ou noeudB
	/*IF (old.a_node_id != 0 AND old.b_node_id != 0) THEN
		--WHEN (new.X1588_87_cmFarEndA != -1 AND old.X1588_88_cmFarEndA != 0 AND old.X1588_90_cmFarEndB != 0)
		--(EXECUTE FUNCTION brasil_TC_notUpdate_FarEndAFarEndB(old.X1588_88_cmFarEndA, old.X1588_90_cmFarEndB) INTO X1588_88_cmFarEndA, X1588_90_cmFarEndB),
		new.a_node_id := old.a_node_id;
		new.b_node_id := old.b_node_id;
	END IF;*/

	--WHEN (new.X1588_87_cmFarEndA = -1) THEN
		--(EXECUTE FUNCTION brasil_TC_notUpdate_farEndACid(old.X1588_87_cmFarEndA) INTO X1588_87_cmFarEndA),

	-- La mise a jour de la table denormalisee est necesssaire quand on fait une modification du numero de VLAN
    IF (new.rpct_type = 'W' AND newAddInfoA IS DISTINCT FROM oldAddInfoA ) THEN
        PERFORM sp_t_res_prod_controlables_updateVLANIdForDTable(new.rpct_id, newAddInfoA, oldAddInfoA);
	END IF;

	IF (new.rpct_vorgang IS DISTINCT FROM '') THEN
		IF (substr(new.rpct_vorgang,1,2) = 'MV') THEN
			PERFORM sp_t_res_prod_controlables_mutationVP(new.rpct_id, '' , new.rpct_vorgang, oldAddInfoA, oldAddInfoB , w_idOldEqA , w_idOldEqB );
		ELSIF (substr(new.rpct_vorgang,1,2) = 'MW') THEN
			PERFORM sp_t_res_prod_controlables_mutationVLAN(new.rpct_id, '', new.rpct_vorgang);
		END IF;
		new.rpct_vorgang = '';
	END IF;
	
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_updatebrasildctrlrscreservevp;
--/
CREATE FUNCTION sp_t_res_prod_controlables_updatebrasildctrlrscreservevp (p_oldid bigint, p_newid bigint, p_oldzubucode character, p_newzubucode character, p_oldinserv bigint, p_newinserv bigint, p_oldinterfaceida character, p_newinterfaceida character)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	IF (p_oldId =0 OR p_oldZubuCode = '' OR p_oldInServ IS NULL OR p_oldInterfaceIdA = '') THEN
		-- Cas de l'insertion
		IF (p_newId IS NOT NULL AND p_newZubuCode = 'V' AND p_newInServ IS NOT NULL AND p_newInterfaceIdA != '') THEN

			UPDATE	t_d_controlable_rscs
			SET		rpct_id = p_newId
			WHERE	rpct_id IS NULL
				AND	a_eqpt_id = p_newInServ
				AND	ctrs_vpia = p_newInterfaceIdA::INT
				AND ctrs_role = 2;

		END IF;

	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_updateprodstatefordtable;
--/
CREATE FUNCTION sp_t_res_prod_controlables_updateprodstatefordtable (p_idrpc bigint, p_newprodstate smallint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN	
	UPDATE t_d_controlable_rscs
	SET ctrs_prod_status = p_newProdState
	WHERE rpct_id = p_idRPC;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_updaterolefordtable;
--/
CREATE FUNCTION sp_t_res_prod_controlables_updaterolefordtable (p_idrsc bigint, p_newrole bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
		
		newRole SMALLINT;
		
	BEGIN
		SELECT CASE WHEN r.role_name LIKE'CHAINAGE%' THEN 1 WHEN r.role_name LIKE 'COLLECTE%' THEN 0 ELSE 1 END  INTO newRole FROM t_roles r WHERE r.role_id = p_newRole;
		--SELECT DECODE(role_name, "CHAINAGE", 1, "COLLECTE", 0, 1) INTO newRole FROM t_roles WHERE role_id = p_newRole;
		UPDATE t_d_controlable_rscs
		SET ctrs_role	 = newRole
		WHERE rpct_id = p_idRsc;
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_controlables_updatevlanidfordtable;
--/
CREATE FUNCTION sp_t_res_prod_controlables_updatevlanidfordtable (p_idvlan bigint, p_newaddinfo brasiltype_addinfo, p_oldaddinfo brasiltype_addinfo)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	IF (p_newAddInfo.interfaceId IS NOT NULL AND p_newAddInfo.interfaceId != p_oldAddInfo.interfaceId) THEN

		UPDATE t_d_controlable_rscs
        	SET ctrs_vpia = p_newAddInfo.interfaceId::INT
        	WHERE rpct_id = p_idVLAN;

	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_roles_del;
--/
CREATE FUNCTION sp_t_res_prod_roles_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	PERFORM sp_t_res_prod_roles_deleteDataFromDTable(OLD.rpct_id, OLD.dslam_eqpt_id, OLD.tsft_id, OLD.nip_eqpt_id);
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_roles_deletedatafromdtable;
--/
CREATE FUNCTION sp_t_res_prod_roles_deletedatafromdtable (p_oldrpctid bigint, p_olddslamid bigint, p_oldtstfid bigint, p_oldnipid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
		--RAISE NOTICE '-------- Debut appel sp_t_res_prod_roles_deleteDataFromDTable';
		DELETE FROM t_d_rsc_dslam_tsfs
			WHERE	rpct_id = p_oldRpctId
				AND	dslam_eqpt_id = p_oldDslamId
				AND	tsft_id = p_oldTstfId
				AND	nip_eqpt_id = p_oldNipId;
		--RAISE NOTICE '-------- Fin appel sp_t_res_prod_roles_deleteDataFromDTable';
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_roles_handledatafordtable;
--/
CREATE FUNCTION sp_t_res_prod_roles_handledatafordtable (pold_rpct_id bigint, pnew_rpct_id bigint, pold_eqpt_id bigint, pold_tstf_id bigint, pold_rpro_priority smallint, pnew_eqpt_id bigint, pnew_tstf_id bigint, pnew_rpro_priority smallint, pold_nip_eqpt_id bigint, pnew_nip_eqpt_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_type CHAR(1);
	w_role SMALLINT;
	w_prodState SMALLINT;
	w_operatorSize INT;
	w_eqptA BIGINT;
	w_portA BIGINT;
	w_eqptB BIGINT;
	w_vpiA INT;
	w_seuil INT;
	w_ctrlSeuil INT;
	
	-- Utilise pour les VP
	w_bemerk2 BrasilType_Bemerk;
	w_nbVCMax INT;

	-- Utilise pour info manElem
	w_saturatedNip CHAR(1);
	w_nipType INTEGER;

	w_modifNIP SMALLINT;
	w_modifProp SMALLINT;
	
	FREE_VC INT;
BEGIN
	
	IF (pNew_rpct_id != 0 AND (pNew_eqpt_id != 0 OR pNew_tstf_id!= 0 OR pNew_rpro_priority != 0)) THEN

		IF (pOld_rpct_id = 0 OR (pOld_eqpt_id = 0 AND pOld_tstf_id = 0 AND pOld_rpro_priority = 0)) THEN

			

			-- La ressource n'a pas encore ete inseree dans la table pour la recherche de ressource
			IF ((SELECT COUNT(*) FROM t_d_controlable_rscs WHERE rpct_id = pNew_rpct_id) = 0) THEN

				-- Recuperation des infos sur la ressource, en mm tps, on verifie qu'elle existe
				-- Attention valeur du name du bangle
				SELECT COUNT(*) INTO w_operatorSize FROM t_net_resource_rels WHERE rpct_id = pNew_rpct_id;				-- Nombre d'operateurs	
				SELECT	rpct.rpct_type,		-- type de la ressource
						CASE WHEN r.role_name LIKE'CHAINAGE%' THEN 1 WHEN r.role_name LIKE 'COLLECTE%' THEN 0 ELSE 1 END,	-- Role de la ressource, chainage, collecte ou matrice
						rpct.rpct_prod_status,						-- Etat de production
						rpct.a_eqpt_id,				-- Eqpt A
						CASE WHEN rpct.rpct_point_a_phys_end_type='P' THEN rpct.a_port_id END,									-- PortA
						rpct.b_eqpt_id,				-- Eqpt B
						CASE WHEN rpct.rpct_type='V' OR rpct.rpct_type='W' THEN rpct.rpct_point_a_interface_id::INT ELSE 0 END, 				-- VpiA
						rpct.rpct_prod_thresold,						-- Seuil
						rpct.rpct_thresold_control,					-- Ctrl Seuil
						rpct.rpct_allocables_vc_count, rpct.rpct_vc_min, rpct.rpct_vc_max, rpct.rpct_nb_locked_ranges
				INTO 	w_type,
						w_role,
						w_prodState,
						w_eqptA,
						w_portA,
						w_eqptB,
						w_vpiA,
						w_seuil,
						w_ctrlSeuil,
						w_bemerk2.allocated_vc_count, w_bemerk2.vc_min, w_bemerk2.vc_max, w_bemerk2.nb_locked_ranges
				--BRASIL-440 - ini:
				--FROM 	t_res_prod_controlables rpct, t_roles r
				--WHERE	rpct.rpct_id = pNew_rpct_id
				--		AND rpct.role_id = r.role_id;
				FROM t_res_prod_controlables rpct
				JOIN t_roles r ON rpct.role_id = r.role_id
				WHERE rpct.rpct_id = pNew_rpct_id;
				--BRASIL-440 - fin:

				-- La ressource n'existe pas
				IF (NOT FOUND) THEN
					PERFORM brasil_raiseException(11, '41');
				END IF;


				-- Traitement table brasilD_controlableRsc

				-- Cas d'un VP
				IF (w_type = 'V') THEN

					--SELECT X4083_5_mychars INTO w_bemerk2 FROM ExternContPers WHERE id = w_externContainerId;

					IF (w_ctrlSeuil = 1) THEN
						w_nbVCMax := brasil_min(w_bemerk2.allocated_vc_count, w_seuil);
					ELSE
						w_nbVCMax := w_bemerk2.allocated_vc_count;
					END IF;
					
					SELECT brasil_free_vc() INTO FREE_VC;

					INSERT INTO t_d_controlable_rscs(rpct_id, ctrs_type, ctrs_role, ctrs_prod_status, ctrs_operator_size, ctrs_full_occupied_status, ctrs_curr_threshold, ctrs_stock_size, ctrs_occupied_count, a_eqpt_id, a_port_id, b_eqpt_id, ctrs_vpia, ctrs_need_new_vc, ctrs_used_count)
					VALUES(	pNew_rpct_id,
							w_type,
							w_role,
							w_prodState,
							w_operatorSize,
							'F',
							brasil_min(w_nbVCMax, FREE_VC),
							w_nbVCMax - brasil_min(w_nbVCMax, FREE_VC),
							0,
							w_eqptA,
							w_portA,
							w_eqptB,
							w_vpiA,
							0,
							0);

					-- Cas d'un VP de collecte
					IF (w_role = 0) THEN

						-- Insertion du bon nombre de vci dans brasilD_rscVci
						--EXECUTE PROCEDURE brasil_addFreeVciForVp(w_idTC, w_bemerk2, w_bemerk2[7,11], brasil_min(w_nbVCMax, $FREE_VC));
						PERFORM brasil_addFreeVciForVp(pNew_rpct_id, w_bemerk2, w_bemerk2.vc_min, brasil_min(w_nbVCMax, FREE_VC));

					END IF;

				ELSE
					-- Cas d'un VLAN ou d'un SrIP
					INSERT INTO t_d_controlable_rscs(rpct_id, ctrs_type, ctrs_role, ctrs_prod_status, ctrs_operator_size, ctrs_full_occupied_status, ctrs_curr_threshold, ctrs_stock_size, ctrs_occupied_count, a_eqpt_id, a_port_id, b_eqpt_id, ctrs_vpia, ctrs_need_new_vc, ctrs_used_count)
					VALUES(	pNew_rpct_id,
							w_type,
							w_role,
							w_prodState,
							w_operatorSize,
							'F',
							CASE WHEN w_ctrlSeuil=1 THEN w_seuil ELSE 1000000 END,
							0,
							0,
							w_eqptA,
							w_portA,
							w_eqptB,
							w_vpiA,
							0,
							0);
							
					
				END IF;

			END IF;

			-- Traitement table brasilD_rscDslamTsf

			-- Recuperation des infos du noeud IP
			IF (pNew_nip_eqpt_id = 0 OR pNew_nip_eqpt_id IS NULL)THEN
				w_saturatedNip := 'N';
				w_nipType := 0;
			ELSE
				-- Recuperation des infos du noeud IP
				SELECT eqpt_saturation_status, eqpt_runtime_type INTO w_saturatedNip, w_nipType FROM t_equipments WHERE eqpt_id = pNew_nip_eqpt_id;
				-- Le manElem n'existe pas
				IF (NOT FOUND) THEN
					PERFORM brasil_raiseException(11, '18');
				END IF;
			END IF;

			
			INSERT INTO t_d_rsc_dslam_tsfs(rpct_id, dslam_eqpt_id, tsft_id, rscd_priority, nip_eqpt_id, rscd_saturated_nip, rscd_nip_type)
			VALUES(	pNew_rpct_id,
					pNew_eqpt_id,
					pNew_tstf_id,
					pNew_rpro_priority,
					pNew_nip_eqpt_id,
					w_saturatedNip,
					w_nipType);


		ELSIF (pNew_nip_eqpt_id != pOld_nip_eqpt_id OR pNew_rpro_priority != pOld_rpro_priority) THEN

			w_modifNIP := 0;
			w_modifProp := 0;

			-- Changement de noeudIP
			IF (pNew_nip_eqpt_id != pOld_nip_eqpt_id) THEN

				w_modifNIP := 1;

				IF (pNew_nip_eqpt_id = 0 OR pNew_nip_eqpt_id IS NULL)THEN
					w_saturatedNip := 'N';
					w_nipType := 0;
				ELSE
					-- Recuperation des infos du noeud IP
					SELECT eqpt_saturation_status, eqpt_runtime_type INTO w_saturatedNip, w_nipType FROM t_equipments WHERE eqpt_id = pNew_nip_eqpt_id;
					-- Le manElem n'existe pas
					IF (NOT FOUND) THEN
						PERFORM brasil_raiseException(11, '18');
					END IF;
				END IF;

			END IF;

			-- Changement de priorite
			IF (pNew_rpro_priority != pOld_rpro_priority) THEN

				w_modifProp := 1;

			END IF;

			
			UPDATE t_d_rsc_dslam_tsfs
				SET	rscd_priority = CASE WHEN w_modifProp=1 THEN pNew_rpro_priority ELSE rscd_priority END,
					nip_eqpt_id = CASE WHEN w_modifNIP=1 THEN pNew_nip_eqpt_id ELSE nip_eqpt_id END,
					rscd_saturated_nip = CASE WHEN w_modifNIP=1 THEN w_saturatedNip ELSE rscd_saturated_nip END,
					rscd_nip_type = CASE WHEN w_modifNIP=1 THEN w_nipType ELSE rscd_nip_type END
				WHERE rpct_id = pNew_rpct_id AND dslam_eqpt_id = pNew_eqpt_id AND tsft_id = pNew_tstf_id;


		END IF;
	END IF;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_roles_handlenipchange;
--/
CREATE FUNCTION sp_t_res_prod_roles_handlenipchange (p_newrpctid bigint, p_newtsft_id bigint, p_oldnip_eqpt_id bigint, p_newnip_eqpt_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_rpc_type		CHAR(1);
	w_mrtAs_id BIGINT;

BEGIN

	-- Traitement uniquement si le nip est modifié et valorisé aprés modif.
	IF ((p_oldNip_eqpt_id IS DISTINCT FROM p_newNip_eqpt_id) AND (p_newNip_eqpt_id IS NOT NULL))
	THEN

		-- Recherche de la TC et du type de RPC
		SELECT	rpc.rpct_type
		INTO 	w_rpc_type
		FROM 	t_res_prod_controlables rpc
		WHERE	rpc.rpct_id = p_newRpctId;

		-- La ressource n'existe pas
		IF (NOT FOUND) THEN
			PERFORM brasil_raiseException(11, '41');
		END IF;

		-- Traitement uniquement si la RPC est un Vlan
		IF (w_rpc_type = 'W') THEN
		
			FOR w_mrtAs_id IN SELECT mrtAs.mras_id 
			FROM t_mrt_access_services mrtAs, t_mrt_access_service_vers mrtAsVers, t_epc_vers_comps epcComp,  t_st_components stComp , t_resource_usages ru 
			WHERE ru.rpct_id=p_newRpctId AND ru.mras_id = mrtAs.mras_id  AND epcComp.mrsv_id = mrtAsVers.mrsv_id 
			AND mrtAsVers.mras_id = ru.mras_id AND stComp.stco_id = epcComp.stco_id AND stComp.tsft_id = p_newTsft_id
			LOOP
				UPDATE t_mrt_access_services SET eqpt_id = p_newNip_eqpt_id WHERE mras_id = w_mrtAs_id;
			
				--RETURN NEXT w_row;
			END LOOP;

		END IF;
	END IF;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_roles_ins;
--/
CREATE FUNCTION sp_t_res_prod_roles_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	w_zero_bigint bigint := 0;
	w_zero_smallint smallint := 0;
BEGIN
	-- FSC T-142 : horodatage de tables en BDD Brasil
	NEW.rpro_creation_time = clock_timestamp(); 
	--PERFORM sp_t_res_prod_roles_checkManElem("", NEW.dslam_eqpt_id);
	PERFORM sp_t_res_prod_roles_handleDataForDTable(w_zero_bigint, NEW.rpct_id, w_zero_bigint,w_zero_bigint,w_zero_smallint, NEW.dslam_eqpt_id, NEW.tsft_id, NEW.rpro_priority, w_zero_bigint, NEW.nip_eqpt_id);
	PERFORM sp_t_res_prod_roles_handleNipChange(NEW.rpct_id, NEW.tsft_id, w_zero_bigint, NEW.nip_eqpt_id);
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_res_prod_roles_upd;
--/
CREATE FUNCTION sp_t_res_prod_roles_upd ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	 --PERFORM sp_t_res_prod_roles_checkManElem(OLD.dslam_eqpt_id, NEW.dslam_eqpt_id);
	 PERFORM sp_t_res_prod_roles_handleDataForDTable(OLD.rpct_id, NEW.rpct_id, OLD.dslam_eqpt_id, OLD.tsft_id, OLD.rpro_priority, NEW.dslam_eqpt_id, NEW.tsft_id, NEW.rpro_priority, OLD.nip_eqpt_id, NEW.nip_eqpt_id);
	 PERFORM sp_t_res_prod_roles_handleNipChange(NEW.rpct_id, NEW.tsft_id, OLD.nip_eqpt_id, NEW.nip_eqpt_id);
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_resource_usages_del;
--/
CREATE FUNCTION sp_t_resource_usages_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_resource_usages_del';
	IF(old.rpct_id IS NOT NULL) THEN
		CASE
			 -- Cas d'une ressource VP qui a ses vci controle
	        WHEN ( old.rsus_resource_role = 0) THEN
	        	PERFORM sp_t_resource_usages_handleDataForDTable(old.mras_id, 1, old.rpct_id, 0::BIGINT, old.rsus_resource_role, 2147483647, old.rsus_vci, 2147483647);
	
	        -- Cas d'une ressource VLAN
	        WHEN (old.rsus_resource_role = 2147483647) THEN
	        	IF (old.mras_id IS NOT NULL) THEN
	               	 PERFORM brasil_updateCompteursVlan(old.rpct_id);
	            END IF;
	                
			-- Cas d'un VP qui est occupe au niveau VP
	        WHEN (old.rsus_resource_role = 3) THEN
	            PERFORM sp_t_resource_usages_handleVPLevelForDTable(1, old.rpct_id, 0::BIGINT, old.rsus_resource_role, 2147483647, old.mras_id);	
	    	ELSE
	    		IF (old.mras_id IS NOT NULL) THEN
	    			-- MAJ de la colonne rpct_allocated_vc_count 
					PERFORM sp_t_resource_usages_updateAllocated_Vc_Count(old.rpct_id, -1);
				END IF;
		END CASE;
	END IF;
    --RAISE NOTICE ' -------- Fin SP sp_t_resource_usages_del';    
	RETURN OLD;
	
END ;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_resource_usages_handledatafordtable;
--/
CREATE FUNCTION sp_t_resource_usages_handledatafordtable (p_oldmrtservice bigint, p_type integer, p_oldrscid bigint, p_newrscid bigint, p_oldrole integer, p_newrole integer, p_oldchannelnumber integer, p_newchannelnumber integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	existMRT INT;
	oldState CHAR(1);
	existRSCVCI INT;
BEGIN
		--RAISE NOTICE ' -------- Debut SP sp_t_resource_usages_handleDataForDTable   - p_type =[%] - p_newRscId = [%] - p_oldRscId = [%] - p_newChannelNumber = [%] - p_oldChannelNumber = [%]',p_type,p_newRscId,p_oldRscId,p_newChannelNumber,p_oldChannelNumber;
	oldState := 'N';
	-- Cas d'une occupation
	IF (p_type = 0) THEN
		IF (p_oldMrtService IS NULL OR p_oldMrtService = 0) THEN
			SELECT rscv_status INTO oldState FROM t_d_rsc_vcis WHERE rpct_id = p_newRscId AND rscv_vci = p_newChannelNumber;
			IF NOT FOUND THEN
				PERFORM brasil_raiseException(11, '7');
			END IF;
			--RAISE NOTICE '--------- oldState = [%]',oldState;
			IF (oldState!='F' AND oldState!='C') THEN
				UPDATE t_d_rsc_vcis
					SET rscv_status = 'O'
						WHERE rpct_id = p_newRscId AND rscv_vci = p_newChannelNumber;
				
				-- MAJ de la colonne rpct_allocated_vc_count 
				--PERFORM sp_t_resource_usages_updateAllocated_Vc_Count(p_newRscId, 1);
			END IF;
		END IF;
	-- Cas d'une liberation
	ELSE
		--Test s'il existe encore une MRTService qui occupe le VCI (cas DM1458)
		SELECT COUNT(rsus_id) INTO existMRT FROM t_resource_usages 
		WHERE rpct_id=p_oldRscId AND rsus_vci=p_oldChannelNumber;
		SELECT COUNT(rpct_id) INTO existRSCVCI FROM t_d_rsc_vcis WHERE rpct_id = p_oldRscId AND rscv_vci = p_oldChannelNumber;
		--RAISE NOTICE 'existMRT = [%] - existRSCVCI = [%]',existMRT,existRSCVCI;
		IF (existRSCVCI!=0) THEN	
			SELECT rscv_status INTO oldState FROM t_d_rsc_vcis WHERE rpct_id = p_oldRscId AND rscv_vci = p_oldChannelNumber;
			
			--On libère le VC si aucune MRT ne l'occupe sauf celle qu'on veut supprimer ou bien dans le cas de co-occupation, ce cas est gerer par un autre trigger
			
			IF (existMRT=0 OR oldState='C') THEN
				UPDATE t_d_rsc_vcis
					SET rscv_status = 'F'
					WHERE rpct_id = p_oldRscId AND rscv_vci = p_oldChannelNumber;
					
				IF NOT FOUND THEN
					PERFORM brasil_raiseException(11, '8');
				END IF;
					
				-- MAJ de la colonne rpct_allocated_vc_count 
				--PERFORM sp_t_resource_usages_updateAllocated_Vc_Count(p_oldRscId, -1);
			END IF;
		END IF;
	END IF;
	
	PERFORM brasil_updateCompteursVpNiveauVc(p_newRscId);
	IF(p_newRscId IS DISTINCT FROM p_oldRscId AND p_oldMrtService IS NOT NULL) THEN
		IF(p_oldRole = 0) THEN
			PERFORM brasil_updateCompteursVpNiveauVc(p_oldRscId);
		ELSE
			PERFORM sp_t_resource_usages_updateAllocated_Vc_Count(p_oldRscId, -1);
		END IF;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_resource_usages_handleDataForDTable';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_resource_usages_handlevplevelfordtable;
--/
CREATE FUNCTION sp_t_resource_usages_handlevplevelfordtable (p_type integer, p_oldrscid bigint, p_newrscid bigint, p_oldrole integer, p_newrole integer, p_mras_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_resource_usages_handleVPLevelForDTable';
	-- Cas d'une occupation
	IF (p_type = 0) THEN
		
		UPDATE t_d_controlable_rscs
		SET ctrs_full_occupied_status = 'O'
		WHERE rpct_id = p_newRscId;

		IF NOT FOUND THEN
			PERFORM brasil_raiseException(11, '80');
		END IF;
		
		IF (p_mras_id IS NOT NULL) THEN
			-- MAJ de la colonne rpct_allocated_vc_count 
			PERFORM brasil_updateCompteursVpNiveauVp(p_newRscId);
		END IF;

	-- Cas d'une liberation
	ELSE
		UPDATE t_d_controlable_rscs
		SET ctrs_full_occupied_status = 'F'
		WHERE rpct_id = p_oldRscId;

		IF NOT FOUND THEN
			PERFORM brasil_raiseException(11, '81');
		END IF;
		
		IF (p_mras_id IS NOT NULL) THEN
			-- MAJ de la colonne rpct_allocated_vc_count 
			PERFORM brasil_updateCompteursVpNiveauVp(p_oldRscId);
		END IF;
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_resource_usages_handleVPLevelForDTable';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_resource_usages_ins;
--/
CREATE FUNCTION sp_t_resource_usages_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_resource_usages_ins';
		 -- Cas d'une ressource qui a ses vci controle
	IF (new.rpct_id IS NOT NULL AND new.mras_id IS NOT NULL) THEN
        IF (new.rsus_resource_role = 0) THEN
        	PERFORM sp_t_resource_usages_handleDataForDTable(0::BIGINT, 0, 0::BIGINT, new.rpct_id, 2147483647, new.rsus_resource_role, 2147483647, new.rsus_vci);

        -- Cas d'un VP qui est occupe au niveau VP
        ELSIF (new.rsus_resource_role = 3) THEN
            PERFORM sp_t_resource_usages_handleVPLevelForDTable(0, 0::BIGINT, new.rpct_id, 2147483647, new.rsus_resource_role, 0::BIGINT);
                
		-- Cas d'une ressource VLAN
        ELSIF (new.rsus_resource_role = 2147483647) THEN
            PERFORM brasil_updateCompteursVlan(new.rpct_id);
        ELSE
	    	-- MAJ de la colonne rpct_allocated_vc_count 
			PERFORM sp_t_resource_usages_updateAllocated_Vc_Count(new.rpct_id, 1);
		END IF;
		
	END IF;
	--RAISE NOTICE ' -------- Fin SP sp_t_resource_usages_ins';        
	RETURN NEW;

END ;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_resource_usages_upd;
--/
CREATE FUNCTION sp_t_resource_usages_upd ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_resource_usages_upd';
	
	--RAISE NOTICE ' -------- old.mras_id : %,new.mras_id : %,old.rpct_id : %,new.rpct_id : %, old.rsus_resource_role : %, new.rsus_resource_role : %',old.mras_id,new.mras_id,old.rpct_id,new.rpct_id,old.rsus_resource_role,new.rsus_resource_role;
	
	CASE
		-- Cas d'une ressource qui a ses vci controle
        WHEN (new.rpct_id IS NOT NULL AND new.rsus_resource_role = 0 AND new.mras_id IS NOT NULL) THEN
			PERFORM sp_t_resource_usages_handleDataForDTable(old.mras_id, 0, old.rpct_id, new.rpct_id, old.rsus_resource_role, new.rsus_resource_role, old.rsus_vci, new.rsus_vci);
--			IF (new.rpct_id IS DISTINCT FROM old.rpct_id AND old.rpct_id is NOT NULL AND old.mras_id IS NOT NULL) THEN
--				PERFORM sp_t_resource_usages_handleDataForDTable(1, old.rpct_id, new.rpct_id, old.rsus_resource_role, new.rsus_resource_role, old.rsus_vci, new.rsus_vci);
--			END IF;

        -- Suppression de l't_resource_usages
        WHEN (new.rpct_id IS NULL AND old.rsus_resource_role = 0 AND old.rpct_id IS NOT NULL) THEN
			PERFORM sp_t_resource_usages_handleDataForDTable(old.mras_id, 1, old.rpct_id, new.rpct_id, old.rsus_resource_role, new.rsus_resource_role, old.rsus_vci, new.rsus_vci);
                
		-- Cas d'un VP qui est occupe au niveau VP
		WHEN (new.rpct_id IS NOT NULL AND new.mras_id IS NOT NULL AND (new.rsus_resource_role = 3 OR new.rsus_resource_role = 4)) THEN
			PERFORM sp_t_resource_usages_handleVPLevelForDTable(0, old.rpct_id, new.rpct_id, old.rsus_resource_role, new.rsus_resource_role, old.mras_id);
			IF (new.rpct_id IS DISTINCT FROM old.rpct_id AND old.rpct_id is NOT NULL AND old.mras_id IS NOT NULL) THEN
				PERFORM sp_t_resource_usages_handleVPLevelForDTable(1, old.rpct_id, new.rpct_id, old.rsus_resource_role, new.rsus_resource_role, old.mras_id);
			END IF;
	
	-- Suppression de l't_resource_usages
		WHEN (new.rpct_id IS NULL AND old.rsus_resource_role = 3 AND old.rpct_id IS NOT NULL) THEN
			PERFORM sp_t_resource_usages_handleVPLevelForDTable(1, old.rpct_id, new.rpct_id, old.rsus_resource_role, new.rsus_resource_role, old.mras_id);

	-- Suppression d'une ressource sur VLAN
	WHEN ((new.mras_id IS DISTINCT FROM old.mras_id OR new.rpct_id IS DISTINCT FROM old.rpct_id) AND new.rsus_resource_role = 2147483647) THEN
		IF (old.rpct_id IS NOT NULL AND old.mras_id IS NOT NULL) THEN
			PERFORM brasil_updateCompteursVlan(old.rpct_id);
		END IF;
		IF (new.rpct_id IS NOT NULL AND new.mras_id IS NOT NULL) THEN
			PERFORM brasil_updateCompteursVlan(new.rpct_id);
		END IF;
    ELSE 
    	-- Cas des autres roles: traitement a remettre si un probleme est detecte pour les roles 2 et 4(il ne faut pas traiter le role 1 dans ce bloc, c'est deja fait par Brasil)
    	IF(new.rpct_id IS NOT NULL AND new.rsus_resource_role IS NOT NULL AND new.mras_id IS NOT NULL) THEN
	    	IF (new.rsus_resource_role != 0 AND new.rsus_resource_role != 3 AND new.rsus_resource_role != 2147483647) THEN
	    		-- MAJ de la colonne rpct_allocated_vc_count par l'ajout de 1 : le cas de decrementation est sera gere par le trigger de suppression
				PERFORM sp_t_resource_usages_updateAllocated_Vc_Count(new.rpct_id, 1);
	    	END IF;
	    	IF (new.rpct_id IS DISTINCT FROM old.rpct_id AND old.rpct_id IS NOT NULL AND old.mras_id IS NOT NULL AND old.rsus_resource_role != 0 AND old.rsus_resource_role != 3 AND old.rsus_resource_role != 2147483647) THEN
	    		-- MAJ de la colonne rpct_allocated_vc_count par l'ajout de 1 : le cas de decrementation est sera gere par le trigger de suppression
				PERFORM sp_t_resource_usages_updateAllocated_Vc_Count(old.rpct_id, -1);
	    	END IF;
   		END IF;
	END CASE;
    --RAISE NOTICE ' -------- Fin SP sp_t_resource_usages_upd';
	RETURN NEW;

END ;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_resource_usages_updateallocated_vc_count;
--/
CREATE FUNCTION sp_t_resource_usages_updateallocated_vc_count (p_resid bigint, p_valtoadd integer)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nbRU INT;
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_resource_usages_updateAllocated_Vc_Count';
	-- Cas d'une occupation
	SELECT COUNT(rpct_id) FROM t_resource_usages INTO w_nbRU WHERE rpct_id = p_resId AND mras_id IS NOT NULL;
	
	UPDATE t_res_prod_controlables 
	SET rpct_allocated_vc_count = w_nbRU --rpct_allocated_vc_count +  p_valToAdd
		WHERE rpct_id = p_resId;
	
	UPDATE t_d_controlable_rscs SET ctrs_occupied_count = w_nbRU WHERE rpct_id = p_resId;
	--RAISE NOTICE ' -------- Fin SP sp_t_resource_usages_updateAllocated_Vc_Count';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_checkandupdslot;
--/
CREATE FUNCTION sp_t_shelfs_checkandupdslot (p_idshelf bigint, p_etatoccupation character)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
	w_nbreLigne INT;
	BEGIN
		--RAISE NOTICE ' -------- Debut SP sp_t_shelfs_checkAndUpdSlot';
        -- Maj du slot
        UPDATE t_slots SET slot_occup_state=p_etatOccupation WHERE shlf_id=p_idShelf;
        -- le slot n'existe pas
        GET DIAGNOSTICS w_nbreLigne = ROW_COUNT; 
	    IF (w_nbreLigne = 0) THEN
				PERFORM brasil_raiseException(11, '23');
		END IF;
        
        --RAISE NOTICE ' -------- Fin SP sp_t_shelfs_checkAndUpdSlot';
    END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_checkdslamlogicalshelf;
--/
CREATE FUNCTION sp_t_shelfs_checkdslamlogicalshelf (p_logicalshelfid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
		--RAISE NOTICE ' -------- Debut SP sp_t_shelfs_checkDslamLogicalShelf';
        -- Recherche du chassis logique
        IF ((SELECT COUNT(*) FROM t_shelfs WHERE shlf_id=p_logicalShelfId AND shlf_type='L')=0) THEN
                PERFORM brasil_raiseException(11, '24');
        END IF;
        --RAISE NOTICE ' -------- Fin SP sp_t_shelfs_checkDslamLogicalShelf';
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_del;
--/
CREATE FUNCTION sp_t_shelfs_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_shelfs_del';
	PERFORM sp_t_shelfs_deleteDataFromDTable(OLD.shlf_id, OLD.shlf_type);
	--RAISE NOTICE ' -------- Fin SP sp_t_shelfs_del';
	RETURN OLD;
	
END ;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_deletedatafromdtable;
--/
CREATE FUNCTION sp_t_shelfs_deletedatafromdtable (p_id bigint, p_shlf_type character)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
		--RAISE NOTICE ' -------- Debut SP sp_t_shelfs_deleteDataFromDTable';
		DELETE FROM t_tst_closed_on_shelfs WHERE shlf_id = p_id;
        IF (p_shlf_type = 'L') THEN
                DELETE FROM t_d_dslam_logical_shelfs WHERE shlf_id = p_id;
                IF FOUND THEN
                	--RAISE NOTICE ' -------- Suppression DONE';
                END IF;
        END IF;
        --RAISE NOTICE ' -------- Fin SP sp_t_shelfs_deleteDataFromDTable';
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_handledatafordtable;
--/
CREATE FUNCTION sp_t_shelfs_handledatafordtable (p_id bigint, p_oldmeid integer, p_newmeid integer, p_oldeqptid bigint, p_neweqptid bigint, p_oldnodeid bigint, p_newnodeid bigint, p_oldprodstate character, p_newprodstate character, p_oldtocmax integer, p_newtocmax integer, p_oldmutation character, p_newmutation character, p_newtype character)  RETURNS character
  VOLATILE
AS $dbvis$
BEGIN
		RAISE NOTICE ' -------- Debut SP sp_t_shelfs_handleDataForDTable';
        -- Cas d'un chassis logique de dslam avec toutes les infos renseignees
        IF (p_newType = 'L' AND p_newMeId != 0 AND p_newNodeId != 0 AND p_newMutation != '' AND p_newProdState != '' AND p_newTocMax != 0) THEN
	        -- le chassis n'a pas encore ete insere
	        IF (p_oldEqptId = 0 OR p_oldMeId = 0 OR p_oldNodeId = 0 OR p_oldMutation = '' OR p_oldProdState = '' OR p_oldTocMax = 0) THEN -- à revoir (est ce que le changement de chaque champs conduit à la création d'une nouvelle ligne dans la table)
	        	RAISE NOTICE ' -------- shlf_id = %', p_id;
	        	RAISE NOTICE ' -------- INSERT INTO t_d_dslam_logical_shelfs';
                		INSERT INTO t_d_dslam_logical_shelfs(
                                shlf_id, eqpt_id, dslam_eqpt_id, node_id, dsls_prod_status, dsls_toc_max, dsls_mutation, dsls_updated,
                                dsls_total_port_count, dsls_total_used_port_count, dsls_mnl_available_port_count, dsls_auto_available_port_count)
                        VALUES (p_id, p_newMeId, p_newEqptId, p_newNodeId, p_newProdState, p_newTocMax, p_newMutation, 0, 0, 0, 0, 0);
       -- l'etat du chassis a ete modifie (prodState, tocMax, mutation)
       ELSIF (p_oldMutation != p_newMutation OR p_oldProdState != p_newProdState OR p_oldTocMax != p_newTocMax) THEN
            UPDATE  t_d_dslam_logical_shelfs
            SET     dsls_prod_status = p_newProdState,
                    dsls_toc_max = p_newTocMax,
                    dsls_mutation = p_newMutation,
                    dsls_updated = 1,
                    dsls_mnl_available_port_count = CASE WHEN p_newProdState = 'F' THEN 0 ELSE dsls_mnl_available_port_count END,
                    dsls_auto_available_port_count = CASE WHEN p_newProdState = 'O' THEN dsls_auto_available_port_count ELSE 0 END 
            WHERE   shlf_id = p_id;
                END IF;
        END IF;
	
        --RAISE NOTICE ' -------- Fin SP sp_t_shelfs_handleDataForDTable';
        RETURN p_newType;
        
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_ins;
--/
CREATE FUNCTION sp_t_shelfs_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_shelfs_ins';
	 -- Cas d'un chassis logique de dslam
	 IF (NEW.shlf_type='P') THEN
		PERFORM sp_t_shelfs_checkDslamLogicalShelf(NEW.logical_shlf_id);
		PERFORM sp_t_shelfs_updateSlot(0, NEW.eqpt_id, NEW.shlf_id);
	 ELSIF (NEW.shlf_type='L') THEN
	 	-- Cas d'un chassis physique de dslam
	 	PERFORM sp_t_shelfs_updateSlot(0, NEW.eqpt_id, NEW.shlf_id);
	 END IF;

	 SELECT sp_t_shelfs_handleDataForDTable(NEW.shlf_id, 0, NEW.eqpt_id_delocalized, 0::bigint, NEW.eqpt_id,  0::bigint, NEW.node_id, '', NEW.shlf_prod_status, 0, NEW.shlf_toc_max, '', NEW.shlf_mutation, NEW.shlf_type) INTO NEW.shlf_type;
		RETURN NEW;
	--RAISE NOTICE ' -------- Fin SP sp_t_shelfs_ins';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_upd;
--/
CREATE FUNCTION sp_t_shelfs_upd ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	
BEGIN
	--RAISE NOTICE ' -------- Debut SP sp_t_shelfs_upd';
	-- Cas d'un chassis dslam
	IF (NEW.shlf_type='P' AND NEW.logical_shlf_id!=OLD.logical_shlf_id) THEN
		--RAISE NOTICE ' -------- Cas d''un chassis dslam';
		PERFORM sp_t_shelfs_checkDslamLogicalShelf(NEW.logical_shlf_id);
	END IF;
	IF (NEW.shlf_type='P' OR NEW.shlf_type='L') THEN
		-- Cas d'un chassis de dslam
		PERFORM sp_t_shelfs_updateSlot(OLD.logical_shlf_id, NEW.logical_shlf_id, NEW.shlf_id);
	END IF;
	IF (NEW.shlf_type='L' AND OLD.shlf_matrix != NEW.shlf_matrix) THEN
		-- Cas de la modification du partie du commentaire du chassis qui indique si les cartes sont matricees ou non.
		PERFORM sp_t_shelfs_updateCardMatrixState(OLD.shlf_id, OLD.shlf_matrix, NEW.shlf_matrix);
	END IF;
	
    SELECT sp_t_shelfs_handleDataForDTable(NEW.shlf_id, OLD.eqpt_id_delocalized, NEW.eqpt_id_delocalized, OLD.eqpt_id,        NEW.eqpt_id,        OLD.node_id,        NEW.node_id,        OLD.shlf_prod_status,      NEW.shlf_prod_status, OLD.shlf_toc_max, NEW.shlf_toc_max, OLD.shlf_mutation, NEW.shlf_mutation, NEW.shlf_type) INTO NEW.shlf_type;
	RETURN NEW;
	--RAISE NOTICE ' -------- Fin SP sp_t_shelfs_upd';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_updatecardmatrixstate;
--/
CREATE FUNCTION sp_t_shelfs_updatecardmatrixstate (chassisid bigint, oldmatrix character, newmatrix character)  RETURNS void
  VOLATILE
AS $dbvis$
DECLARE
    	counter INT;
    	slotNo INT;
    	cardId BIGINT;
    	aSoustraire INT:=0;
    BEGIN
	    --RAISE NOTICE ' -------- Debut sp_t_shelfs_updateCardMatrixState';
    	counter = 1;
    	SELECT MIN(slot.slot_num) INTO  slotNo FROM t_shelfs shelf, t_slots slot WHERE slot.shlf_id=shelf.shlf_id AND  shelf.shlf_id=chassisId;
        
        IF (slotNo = 0) THEN
        	aSoustraire := 1;
        END IF;
    	LOOP
    		--RAISE NOTICE ' -------- counter = %',counter;
    		IF(counter > 25) THEN
    			--RAISE NOTICE ' -------- EXIT';
    			EXIT;
    		ELSE
    			--RAISE NOTICE ' -------- oldMatrix = % - newMatrix = %',SUBSTRING(oldMatrix FROM counter FOR 1), SUBSTRING(newMatrix FROM counter FOR 1);
    			IF (SUBSTRING(oldMatrix FROM counter FOR 1)!=SUBSTRING(newMatrix FROM counter FOR 1)) THEN
    			
    						--BRASIL-440 - ini: 
                            --    SELECT card.card_id 
                            --    INTO  cardId 
                            --   FROM t_shelfs shelf, t_cards card, t_slots slot 
                            --    WHERE card.slot_id = slot.slot_id 
                            --    AND slot.shlf_id=shelf.shlf_id 
                            --    AND card.card_runtime_type IN ('D', 'F') 
                            --    AND card.card_num=counter - aSoustraire
                            --    AND  shelf.shlf_id=chassisId;
                                
                                SELECT card.card_id 
								  INTO cardId 
								  FROM t_slots slot 
								  JOIN t_cards card ON card.slot_id = slot.slot_id 
								  JOIN t_shelfs shelf ON slot.shlf_id=shelf.shlf_id 
								 WHERE card.card_runtime_type IN ('D', 'F') 
								   AND card.card_num=counter - aSoustraire
								   AND shelf.shlf_id=chassisId;
                            --BRASIL-440 - fin:
                                IF (FOUND) THEN
	                                UPDATE t_d_dslam_xdsl_cards 
	                                SET dxcd_matrix=SUBSTRING(newMatrix FROM counter FOR 1)  
	                                WHERE card_id=cardId;
                                END IF;
		        END IF;
		        counter = counter + 1;
    		END IF;
    	END LOOP;
    	--RAISE NOTICE ' -------- Fin sp_t_shelfs_updateCardMatrixState';
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_shelfs_updateslot;
--/
CREATE FUNCTION sp_t_shelfs_updateslot (p_oldusereqid bigint, p_newusereqid bigint, p_idshelf bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
		--RAISE NOTICE ' -------- Debut SP sp_t_shelfs_updateSlot';
		
		IF (p_newUserEqId > 0) THEN
			IF (p_oldUserEqId > 0) THEN
				PERFORM sp_t_shelfs_checkAndUpdSlot(p_idShelf, 'O');
			END IF;
        ELSIF (p_oldUserEqId > 0) THEN
			-- Maj ancienne alveole
            PERFORM sp_t_shelfs_checkAndUpdSlot(p_idShelf, 'L');
		END IF;
		
		--RAISE NOTICE ' -------- Fin SP sp_t_shelfs_updateSlot';
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_slots_upd_supportedequipsize;
--/
CREATE FUNCTION sp_t_slots_upd_supportedequipsize ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
	IF(NEW.slot_occup_state='O' AND OLD.slot_occup_state='O') THEN
		PERFORM brasil_raiseException(11, '54');
	END IF;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_stripes_upd_name;
--/
CREATE FUNCTION sp_t_stripes_upd_name ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
	IF(OLD.strp_module != NEW.strp_module OR OLD.strp_up_range != NEW.strp_up_range OR OLD.strp_down_range != NEW.strp_down_range
	OR OLD.strp_up_level != NEW.strp_up_level OR OLD.strp_down_level != NEW.strp_down_level) THEN
		PERFORM sp_t_stripes_updateDataForDTable(OLD.strp_id, NEW.strp_module, NEW.strp_up_range, NEW.strp_down_range,new.strp_up_level, NEW.strp_down_level);
	END IF;
RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_stripes_updatedatafordtable;
--/
CREATE FUNCTION sp_t_stripes_updatedatafordtable (p_idreglette bigint, p_module character, p_uprange smallint, p_downrange smallint, p_uplevel integer, p_downlevel integer)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	UPDATE  t_d_xdsl_card_stripes
	SET	xdcs_module = p_module,
		xdcs_up_range =  p_upRange,
		xdcs_down_range = p_downRange,
		xdcs_up_level =  p_upLevel,
		xdcs_down_level = p_downLevel
	WHERE strp_id = p_idReglette;
	
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_tr_assignments_del;
--/
CREATE FUNCTION sp_t_tr_assignments_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN	
		PERFORM sp_t_tr_assignments_deleteParts(OLD.tass_id);
RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_tr_assignments_deleteparts;
--/
CREATE FUNCTION sp_t_tr_assignments_deleteparts (p_rtassignmentid bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	DELETE FROM t_resource_constraints WHERE tass_id = p_rtAssignmentId;
	DELETE FROM t_usage_constraints WHERE tass_id = p_rtAssignmentId;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_vc_lock_ranges_del;
--/
CREATE FUNCTION sp_t_vc_lock_ranges_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
BEGIN
	PERFORM brasil_updateAllocableVc_lockedRange(old.rpct_id);
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_vc_lock_ranges_ins;
--/
CREATE FUNCTION sp_t_vc_lock_ranges_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
BEGIN
	PERFORM brasil_updateAllocableVc_lockedRange(new.rpct_id);
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_t_vc_lock_ranges_upd;
--/
CREATE FUNCTION sp_t_vc_lock_ranges_upd ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
BEGIN
	IF (old.vckr_vc_max != new.vckr_vc_max OR old.vckr_vc_min != new.vckr_vc_min) THEN
		PERFORM brasil_updateAllocableVc_lockedRange(new.rpct_id);
	END IF;
	RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_tr_t_equipments_del;
--/
CREATE FUNCTION sp_tr_t_equipments_del ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	
BEGIN	
	--RAISE NOTICE ' -------- Debut SP sp_tr_t_equipments_del';
	PERFORM sp_t_equipments_deleteDataFromDTable(OLD.eqpt_id, OLD.eqpt_runtime_type);
	--RAISE NOTICE ' -------- Fin SP sp_tr_t_equipments_del';
	RETURN OLD;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_tr_t_equipments_ins;
--/
CREATE FUNCTION sp_tr_t_equipments_ins ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	newRingId BrasilType_RingTab;
	newconfig BrasilType_ConfigTab;
	oldRingId BrasilType_RingTab;
	oldconfig BrasilType_ConfigTab;
BEGIN	
	--RAISE NOTICE ' -------- Debut SP sp_tr_t_equipments_ins';
		newRingId.source := NEW.source_eqpt_id ;
		newRingId.maitre := NEW.master_eqpt_id ;
		newRingId.rank   := NEW.eqpt_rank ;
		
		newconfig.equiptStatus := NEW.eqpt_status;
		newconfig.prodStatus := NEW.eqpt_prod_status;
		
			 -- cas d'un Dslam avec configuration != ""
			IF (NEW.eqpt_runtime_type = 1 AND NEW.manager_eqpt_id != 0) THEN
			    PERFORM sp_t_equipments_checkGestDslam(NEW.manager_eqpt_id);
			END IF;
			    
			-- La verif du maitre et du dslam reel sont faites dans rechercheBroche car besoin nouvelle valeur de ringId
			IF (NEW.eqpt_runtime_type = 1 OR NEW.eqpt_runtime_type = 3) THEN
			newRingId :=  sp_t_equipments_handleDataForDTable(NEW.eqpt_id, 0::smallint, NEW.eqpt_runtime_type, 0, NEW.eqpt_id_real_dslam, 0::bigint, NEW.node_id, oldconfig, newconfig, oldRingId, newRingId);
			    			
				NEW.source_eqpt_id := newRingId.source;
				NEW.master_eqpt_id := newRingId.maitre;
				NEW.eqpt_rank  			:= newRingId.rank;
				
			END IF;
	  
	  RETURN NEW;
	--RAISE NOTICE ' -------- Fin SP sp_tr_t_equipments_ins';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_tr_t_equipments_upd;
--/
CREATE FUNCTION sp_tr_t_equipments_upd ()  RETURNS trigger
  VOLATILE
AS $dbvis$
DECLARE
	p_newRingId BrasilType_RingTab;
	p_oldRingId BrasilType_RingTab;
	newconfig BrasilType_ConfigTab;
	oldconfig BrasilType_ConfigTab;
	newRingId BrasilType_RingTab;
BEGIN	
		--RAISE NOTICE ' -------- Debut SP sp_tr_t_equipments_upd';
		p_oldRingId.source := OLD.source_eqpt_id ;
		p_oldRingId.maitre := OLD.master_eqpt_id ;
		p_oldRingId.rank   := OLD.eqpt_rank ;

		p_newRingId.source := NEW.source_eqpt_id ;
		p_newRingId.maitre := NEW.master_eqpt_id ;
		p_newRingId.rank   := NEW.eqpt_rank ;
		
		
		oldconfig.equiptStatus := OLD.eqpt_status;
		oldconfig.prodStatus := OLD.eqpt_prod_status;
		
		newconfig.equiptStatus := NEW.eqpt_status;
		newconfig.prodStatus := NEW.eqpt_prod_status;
		
		  -- cas d'un Dslam avec changement de gestionnaire
		 IF (NEW.eqpt_runtime_type = 1 AND NEW.manager_eqpt_id != OLD.manager_eqpt_id) THEN
		    PERFORM sp_t_equipments_checkGestDslam(NEW.manager_eqpt_id);
		    
		 -- La verif du maitre et du dslam reel sont faites dans rechercheBroche car besoin nouvelle valeur de ringId
		 ELSIF (NEW.eqpt_runtime_type = 1 OR NEW.eqpt_runtime_type = 3) THEN
		 --RAISE NOTICE ' -------- Debut eqpt_runtime_type = 3';
				-- bigint, smallint, smallint, integer, integer, bigint,  bigint, BrasilType_ConfigTab, BrasilType_ConfigTab, BrasilType_RingTab, ring_tab
				
				-- bigint, smallint,  smallint, integer, integer, bigint, bigint, BrasilType_ConfigTab, BrasilType_ConfigTab, BrasilType_RingTab, ring_tab
		    newRingId :=   sp_t_equipments_handleDataForDTable(NEW.eqpt_id, OLD.eqpt_runtime_type, NEW.eqpt_runtime_type, OLD.eqpt_id_real_dslam, NEW.eqpt_id_real_dslam, OLD.node_id, NEW.node_id, oldconfig, newconfig, p_oldRingId, p_newRingId);
		 		
		 		NEW.source_eqpt_id := p_newRingId.source;
				NEW.master_eqpt_id := p_newRingId.maitre;
				NEW.eqpt_rank  			:= p_newRingId.rank;
		 --RAISE NOTICE ' -------- Fin eqpt_runtime_type = 3';   
		  ELSIF (NEW.eqpt_saturation_status != OLD.eqpt_saturation_status AND OLD.eqpt_saturation_status != '') THEN
		    PERFORM  sp_t_equipments_updateDataForResourceDTable(NEW.eqpt_id, NEW.eqpt_saturation_status);
		    
	    END IF;
	  RETURN NEW;
	  --RAISE NOTICE ' -------- Debut SP sp_tr_t_equipments_upd';
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_updateoldg;
--/
CREATE FUNCTION sp_updateoldg (p_pogr_id bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN

	-- Maj des points du groupe
	UPDATE t_ports  SET port_occup_ont=port_occup_ont-1,
		port_logical_occup_cpt = COALESCE(port_logical_occup_cpt, 0)-1
	WHERE pogr_id = p_pogr_id;
	
	

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION sp_updateoldp;
--/
CREATE FUNCTION sp_updateoldp (p_idpoint bigint)  RETURNS void
  VOLATILE
AS $dbvis$
BEGIN
	UPDATE t_ports SET port_occup_ont=port_occup_ont-1,
		port_logical_occup_cpt = COALESCE(port_logical_occup_cpt, 0) - 1
		WHERE port_id=p_idPoint;

END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION t_res_prod_controlables_updatecompteurs_karma;
--/
CREATE FUNCTION t_res_prod_controlables_updatecompteurs_karma ()  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE
		w_rpct_id BIGINT;
	BEGIN        
		FOR w_rpct_id IN (SELECT rpct_id FROM tempTableInfosBaseRpctId)
               		LOOP
                        	PERFORM brasil_updateCompteursVlan(w_rpct_id);
		        END LOOP;	
		RETURN 0;
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_card_creation_time_function;
--/
CREATE FUNCTION update_card_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.card_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_card_last_modification_time_function;
--/
CREATE FUNCTION update_card_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.card_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_ctrs_creation_time_function;
--/
CREATE FUNCTION update_ctrs_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.ctrs_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_ctrs_last_modification_time_function;
--/
CREATE FUNCTION update_ctrs_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.ctrs_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_dsac_creation_time_function;
--/
CREATE FUNCTION update_dsac_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.dsac_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_dsac_last_modification_time_function;
--/
CREATE FUNCTION update_dsac_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.dsac_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_dsag_creation_time_function;
--/
CREATE FUNCTION update_dsag_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.dsag_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_dsag_last_modification_time_function;
--/
CREATE FUNCTION update_dsag_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.dsag_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_eqpt_creation_time_function;
--/
CREATE FUNCTION update_eqpt_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.eqpt_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_eqpt_last_modification_time_function;
--/
CREATE FUNCTION update_eqpt_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.eqpt_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_evim_creation_time_function;
--/
CREATE FUNCTION update_evim_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.evim_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_evim_last_modification_time_function;
--/
CREATE FUNCTION update_evim_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.evim_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_mdlk_last_modification_time_function;
--/
CREATE FUNCTION update_mdlk_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.mdlk_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_mkfl_last_modification_time_function;
--/
CREATE FUNCTION update_mkfl_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.mkfl_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_mras_creation_time_function;
--/
CREATE FUNCTION update_mras_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.mras_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_mras_last_modification_time_function;
--/
CREATE FUNCTION update_mras_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.mras_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_mrvi_last_modification_time_function;
--/
CREATE FUNCTION update_mrvi_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.mrvi_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_nrre_creation_time_function;
--/
CREATE FUNCTION update_nrre_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.nrre_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_nrre_last_modification_time_function;
--/
CREATE FUNCTION update_nrre_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.nrre_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_pogr_creation_time_function;
--/
CREATE FUNCTION update_pogr_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.pogr_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_pogr_last_modification_time_function;
--/
CREATE FUNCTION update_pogr_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.pogr_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_port_last_modification_time_function;
--/
CREATE FUNCTION update_port_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.port_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_rpct_creation_time_function;
--/
CREATE FUNCTION update_rpct_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    -- ASSUMES the table has a column named exactly "rpct_creation_time".
    -- Fetch date-time of actual current moment from clock, rather than start of statement or start of transaction.
    NEW.rpct_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_rpct_last_modification_time_function;
--/
CREATE FUNCTION update_rpct_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    -- ASSUMES the table has a column named exactly "rpct_last_modification_time".
    -- Fetch date-time of actual current moment from clock, rather than start of statement or start of transaction.
    NEW.rpct_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_rpro_last_modification_time_function;
--/
CREATE FUNCTION update_rpro_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.rpro_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_rscv_creation_time_function;
--/
CREATE FUNCTION update_rscv_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.rscv_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_rscv_last_modification_time_function;
--/
CREATE FUNCTION update_rscv_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.rscv_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_rsus_creation_time_function;
--/
CREATE FUNCTION update_rsus_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.rsus_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_rsus_last_modification_time_function;
--/
CREATE FUNCTION update_rsus_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.rsus_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_shlf_creation_time_function;
--/
CREATE FUNCTION update_shlf_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.shlf_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_shlf_last_modification_time_function;
--/
CREATE FUNCTION update_shlf_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.shlf_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_slot_creation_time_function;
--/
CREATE FUNCTION update_slot_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.slot_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_slot_last_modification_time_function;
--/
CREATE FUNCTION update_slot_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.slot_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_strp_creation_time_function;
--/
CREATE FUNCTION update_strp_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.strp_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_strp_last_modification_time_function;
--/
CREATE FUNCTION update_strp_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.strp_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_vckr_creation_time_function;
--/
CREATE FUNCTION update_vckr_creation_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.vckr_creation_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION update_vckr_last_modification_time_function;
--/
CREATE FUNCTION update_vckr_last_modification_time_function ()  RETURNS trigger
  VOLATILE
AS $dbvis$
BEGIN
    NEW.vckr_last_modification_time = clock_timestamp(); 
    RETURN NEW;
END;
$dbvis$ LANGUAGE plpgsql
/
DROP FUNCTION updateutilisation;
--/
CREATE FUNCTION updateutilisation (pnd character varying)  RETURNS integer
  VOLATILE
AS $dbvis$
DECLARE
		mrasId BIGINT;
	BEGIN        
		FOR mrasId IN (SELECT mrtaccessserviceid  FROM tempTableInputUtilisation WHERE nd = pNd)
		LOOP
			UPDATE t_mrt_access_services SET mras_utilisation = ((
		        SELECT	utilisation
				FROM	tempTableInputUtilisation 
				WHERE	t_mrt_access_services.mras_id = tempTableInputUtilisation.mrtaccessserviceid
			)) 
			WHERE mras_id = mrasId;
			IF (FOUND) THEN
				RAISE NOTICE 'Mise à jour de la mrtAccessService % pour le ND %',mrasId,pNd;
			END IF;
		END LOOP;
		
		RETURN 0;
	EXCEPTION
		WHEN DEADLOCK_DETECTED THEN 
			RETURN 1;
		WHEN OTHERS THEN
			RETURN 2;
		
	END;
$dbvis$ LANGUAGE plpgsql
/
DROP TRIGGER tr_t_card_national_profiles_del ON t_card_national_profiles CASCADE;
--/
CREATE TRIGGER tr_t_card_national_profiles_del
  BEFORE DELETE ON t_card_national_profiles
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_card_national_profiles_del()
/
DROP TRIGGER tr_t_card_national_profiles_upd ON t_card_national_profiles CASCADE;
--/
CREATE TRIGGER tr_t_card_national_profiles_upd
  BEFORE UPDATE ON t_card_national_profiles
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_card_national_profiles_upd()
/
DROP TRIGGER tr_t_cards_before_update ON t_cards CASCADE;
--/
CREATE TRIGGER tr_t_cards_before_update
  BEFORE UPDATE ON t_cards
  FOR EACH ROW
EXECUTE PROCEDURE update_card_last_modification_time_function()
/
DROP TRIGGER tr_t_cards_del ON t_cards CASCADE;
--/
CREATE TRIGGER tr_t_cards_del
  BEFORE DELETE ON t_cards
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_cards_del()
/
DROP TRIGGER tr_t_cards_ins ON t_cards CASCADE;
--/
CREATE TRIGGER tr_t_cards_ins
  AFTER INSERT ON t_cards
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_cards_ins()
/
DROP TRIGGER tr_t_cards_ins_before ON t_cards CASCADE;
--/
CREATE TRIGGER tr_t_cards_ins_before
  BEFORE INSERT ON t_cards
  FOR EACH ROW
EXECUTE PROCEDURE update_card_creation_time_function()
/
DROP TRIGGER tr_t_cards_upd ON t_cards CASCADE;
--/
CREATE TRIGGER tr_t_cards_upd
  BEFORE UPDATE ON t_cards
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_cards_upd()
/
DROP TRIGGER tr_t_cards_upd_slot ON t_cards CASCADE;
--/
CREATE TRIGGER tr_t_cards_upd_slot
  BEFORE UPDATE ON t_cards
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_cards_upd_slot()
/
DROP TRIGGER tr_t_d_controlable_rscs_before_update ON t_d_controlable_rscs CASCADE;
--/
CREATE TRIGGER tr_t_d_controlable_rscs_before_update
  BEFORE UPDATE ON t_d_controlable_rscs
  FOR EACH ROW
EXECUTE PROCEDURE update_ctrs_last_modification_time_function()
/
DROP TRIGGER tr_t_d_controlable_rscs_ins ON t_d_controlable_rscs CASCADE;
--/
CREATE TRIGGER tr_t_d_controlable_rscs_ins
  AFTER INSERT ON t_d_controlable_rscs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_d_controlable_rscs_ins()
/
DROP TRIGGER tr_t_d_controlable_rscs_ins_before ON t_d_controlable_rscs CASCADE;
--/
CREATE TRIGGER tr_t_d_controlable_rscs_ins_before
  BEFORE INSERT ON t_d_controlable_rscs
  FOR EACH ROW
EXECUTE PROCEDURE update_ctrs_creation_time_function()
/
DROP TRIGGER tr_t_d_controlable_rscs_upd_fulloccstate ON t_d_controlable_rscs CASCADE;
--/
CREATE TRIGGER tr_t_d_controlable_rscs_upd_fulloccstate
  BEFORE UPDATE ON t_d_controlable_rscs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_d_controlable_rscs_upd_fulloccstate()
/
DROP TRIGGER tr_t_d_controlable_rscs_upd_occupiedcount ON t_d_controlable_rscs CASCADE;
--/
CREATE TRIGGER tr_t_d_controlable_rscs_upd_occupiedcount
  BEFORE UPDATE ON t_d_controlable_rscs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_d_controlable_rscs_upd_occupiedcount()
/
DROP TRIGGER tr_t_d_dslam_logical_shelfs_del ON t_d_dslam_logical_shelfs CASCADE;
--/
CREATE TRIGGER tr_t_d_dslam_logical_shelfs_del
  BEFORE DELETE ON t_d_dslam_logical_shelfs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_d_dslam_logical_shelfs_del()
/
DROP TRIGGER tr_t_d_dslam_logical_shelfs_upd_updated ON t_d_dslam_logical_shelfs CASCADE;
--/
CREATE TRIGGER tr_t_d_dslam_logical_shelfs_upd_updated
  BEFORE UPDATE ON t_d_dslam_logical_shelfs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_d_dslam_logical_shelfs_upd_updated()
/
DROP TRIGGER tr_t_d_dslam_xdsl_cards_del ON t_d_dslam_xdsl_cards CASCADE;
--/
CREATE TRIGGER tr_t_d_dslam_xdsl_cards_del
  BEFORE DELETE ON t_d_dslam_xdsl_cards
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_d_dslam_xdsl_cards_del()
/
DROP TRIGGER tr_t_d_dslam_xdsl_cards_upd ON t_d_dslam_xdsl_cards CASCADE;
--/
CREATE TRIGGER tr_t_d_dslam_xdsl_cards_upd
  BEFORE UPDATE ON t_d_dslam_xdsl_cards
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_d_dslam_xdsl_cards_upd()
/
DROP TRIGGER tr_t_d_rsc_vcis_before_update ON t_d_rsc_vcis CASCADE;
--/
CREATE TRIGGER tr_t_d_rsc_vcis_before_update
  BEFORE UPDATE ON t_d_rsc_vcis
  FOR EACH ROW
EXECUTE PROCEDURE update_rscv_last_modification_time_function()
/
DROP TRIGGER tr_t_d_rsc_vcis_ins_before ON t_d_rsc_vcis CASCADE;
--/
CREATE TRIGGER tr_t_d_rsc_vcis_ins_before
  BEFORE INSERT ON t_d_rsc_vcis
  FOR EACH ROW
EXECUTE PROCEDURE update_rscv_creation_time_function()
/
DROP TRIGGER tr_t_d_rsc_vcis_upd_state ON t_d_rsc_vcis CASCADE;
--/
CREATE TRIGGER tr_t_d_rsc_vcis_upd_state
  BEFORE UPDATE ON t_d_rsc_vcis
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_d_rsc_vcis_upd_state()
/
DROP TRIGGER tr_t_distributors_del ON t_distributors CASCADE;
--/
CREATE TRIGGER tr_t_distributors_del
  BEFORE DELETE ON t_distributors
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_distributors_del()
/
DROP TRIGGER tr_t_dslam_access_constraints_before_update ON t_dslam_access_constraints CASCADE;
--/
CREATE TRIGGER tr_t_dslam_access_constraints_before_update
  BEFORE UPDATE ON t_dslam_access_constraints
  FOR EACH ROW
EXECUTE PROCEDURE update_dsac_last_modification_time_function()
/
DROP TRIGGER tr_t_dslam_access_constraints_ins_before ON t_dslam_access_constraints CASCADE;
--/
CREATE TRIGGER tr_t_dslam_access_constraints_ins_before
  BEFORE INSERT ON t_dslam_access_constraints
  FOR EACH ROW
EXECUTE PROCEDURE update_dsac_creation_time_function()
/
DROP TRIGGER tr_t_dslam_assignments_before_update ON t_dslam_assignments CASCADE;
--/
CREATE TRIGGER tr_t_dslam_assignments_before_update
  BEFORE UPDATE ON t_dslam_assignments
  FOR EACH ROW
EXECUTE PROCEDURE update_dsag_last_modification_time_function()
/
DROP TRIGGER tr_t_dslam_assignments_del ON t_dslam_assignments CASCADE;
--/
CREATE TRIGGER tr_t_dslam_assignments_del
  BEFORE DELETE ON t_dslam_assignments
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_dslam_assignments_del()
/
DROP TRIGGER tr_t_dslam_assignments_ins_before ON t_dslam_assignments CASCADE;
--/
CREATE TRIGGER tr_t_dslam_assignments_ins_before
  BEFORE INSERT ON t_dslam_assignments
  FOR EACH ROW
EXECUTE PROCEDURE update_dsag_creation_time_function()
/
DROP TRIGGER tr_t_epc_order_lines_del ON t_epc_order_lines CASCADE;
--/
CREATE TRIGGER tr_t_epc_order_lines_del
  BEFORE DELETE ON t_epc_order_lines
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_epc_order_lines_del()
/
DROP TRIGGER tr_t_epc_vers_del ON t_epc_vers CASCADE;
--/
CREATE TRIGGER tr_t_epc_vers_del
  BEFORE DELETE ON t_epc_vers
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_epc_vers_del()
/
DROP TRIGGER tr_t_epc_vers_upd_state ON t_epc_vers CASCADE;
--/
CREATE TRIGGER tr_t_epc_vers_upd_state
  AFTER UPDATE ON t_epc_vers
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_epc_vers_upd_state()
/
DROP TRIGGER tr_t_epc_vers_impacts_before_update ON t_epc_vers_impacts CASCADE;
--/
CREATE TRIGGER tr_t_epc_vers_impacts_before_update
  BEFORE UPDATE ON t_epc_vers_impacts
  FOR EACH ROW
EXECUTE PROCEDURE update_evim_last_modification_time_function()
/
DROP TRIGGER tr_t_epc_vers_impacts_ins_before ON t_epc_vers_impacts CASCADE;
--/
CREATE TRIGGER tr_t_epc_vers_impacts_ins_before
  BEFORE INSERT ON t_epc_vers_impacts
  FOR EACH ROW
EXECUTE PROCEDURE update_evim_creation_time_function()
/
DROP TRIGGER tr_t_epcs_del ON t_epcs CASCADE;
--/
CREATE TRIGGER tr_t_epcs_del
  BEFORE DELETE ON t_epcs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_epcs_del()
/
DROP TRIGGER tr_t_epcs_ins ON t_epcs CASCADE;
--/
CREATE TRIGGER tr_t_epcs_ins
  BEFORE INSERT ON t_epcs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_epcs_ins()
/
DROP TRIGGER tr_t_epcs_upd_value ON t_epcs CASCADE;
--/
CREATE TRIGGER tr_t_epcs_upd_value
  BEFORE UPDATE ON t_epcs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_epcs_upd_value()
/
DROP TRIGGER tr_t_equipments_before_update ON t_equipments CASCADE;
--/
CREATE TRIGGER tr_t_equipments_before_update
  BEFORE UPDATE ON t_equipments
  FOR EACH ROW
EXECUTE PROCEDURE update_eqpt_last_modification_time_function()
/
DROP TRIGGER tr_t_equipments_del ON t_equipments CASCADE;
--/
CREATE TRIGGER tr_t_equipments_del
  BEFORE DELETE ON t_equipments
  FOR EACH ROW
EXECUTE PROCEDURE sp_tr_t_equipments_del()
/
DROP TRIGGER tr_t_equipments_ins ON t_equipments CASCADE;
--/
CREATE TRIGGER tr_t_equipments_ins
  AFTER INSERT ON t_equipments
  FOR EACH ROW
EXECUTE PROCEDURE sp_tr_t_equipments_ins()
/
DROP TRIGGER tr_t_equipments_ins_before ON t_equipments CASCADE;
--/
CREATE TRIGGER tr_t_equipments_ins_before
  BEFORE INSERT ON t_equipments
  FOR EACH ROW
EXECUTE PROCEDURE update_eqpt_creation_time_function()
/
DROP TRIGGER tr_t_equipments_upd ON t_equipments CASCADE;
--/
CREATE TRIGGER tr_t_equipments_upd
  BEFORE UPDATE ON t_equipments
  FOR EACH ROW
EXECUTE PROCEDURE sp_tr_t_equipments_upd()
/
DROP TRIGGER tr_t_making_files_before_update ON t_making_files CASCADE;
--/
CREATE TRIGGER tr_t_making_files_before_update
  BEFORE UPDATE ON t_making_files
  FOR EACH ROW
EXECUTE PROCEDURE update_mkfl_last_modification_time_function()
/
DROP TRIGGER tr_t_making_files_del ON t_making_files CASCADE;
--/
CREATE TRIGGER tr_t_making_files_del
  BEFORE DELETE ON t_making_files
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_making_files_del()
/
DROP TRIGGER tr_t_media_links_before_update ON t_media_links CASCADE;
--/
CREATE TRIGGER tr_t_media_links_before_update
  BEFORE UPDATE ON t_media_links
  FOR EACH ROW
EXECUTE PROCEDURE update_mdlk_last_modification_time_function()
/
DROP TRIGGER tr_t_media_links_del ON t_media_links CASCADE;
--/
CREATE TRIGGER tr_t_media_links_del
  BEFORE DELETE ON t_media_links
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_media_links_del()
/
DROP TRIGGER tr_t_media_links_ins ON t_media_links CASCADE;
--/
CREATE TRIGGER tr_t_media_links_ins
  BEFORE INSERT ON t_media_links
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_media_links_ins()
/
DROP TRIGGER tr_t_media_links_mutation ON t_media_links CASCADE;
--/
CREATE TRIGGER tr_t_media_links_mutation
  AFTER UPDATE ON t_media_links
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_media_links_mutation()
/
DROP TRIGGER tr_t_media_links_update ON t_media_links CASCADE;
--/
CREATE TRIGGER tr_t_media_links_update
  BEFORE UPDATE ON t_media_links
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_media_links_update()
/
DROP TRIGGER tr_t_mrt_access_dslam_vers_del ON t_mrt_access_dslam_vers CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_dslam_vers_del
  BEFORE DELETE ON t_mrt_access_dslam_vers
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_access_dslam_vers_del()
/
DROP TRIGGER tr_t_mrt_access_dslams_del ON t_mrt_access_dslams CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_dslams_del
  AFTER DELETE ON t_mrt_access_dslams
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_access_dslams_del()
/
DROP TRIGGER tr_t_mrt_access_dslams_ins ON t_mrt_access_dslams CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_dslams_ins
  BEFORE INSERT ON t_mrt_access_dslams
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_access_dslams_ins_update()
/
DROP TRIGGER tr_t_mrt_access_dslams_update ON t_mrt_access_dslams CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_dslams_update
  BEFORE UPDATE ON t_mrt_access_dslams
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_access_dslams_ins_update()
/
DROP TRIGGER tr_t_mrt_access_service_vers_del ON t_mrt_access_service_vers CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_service_vers_del
  BEFORE DELETE ON t_mrt_access_service_vers
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_access_service_vers_del()
/
DROP TRIGGER tr_t_mrt_access_service_del ON t_mrt_access_services CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_service_del
  BEFORE DELETE ON t_mrt_access_services
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_access_services_del()
/
DROP TRIGGER tr_t_mrt_access_services_before_update ON t_mrt_access_services CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_services_before_update
  BEFORE UPDATE ON t_mrt_access_services
  FOR EACH ROW
EXECUTE PROCEDURE update_mras_last_modification_time_function()
/
DROP TRIGGER tr_t_mrt_access_services_ins_before ON t_mrt_access_services CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_services_ins_before
  BEFORE INSERT ON t_mrt_access_services
  FOR EACH ROW
EXECUTE PROCEDURE update_mras_creation_time_function()
/
DROP TRIGGER tr_t_mrt_access_services_update ON t_mrt_access_services CASCADE;
--/
CREATE TRIGGER tr_t_mrt_access_services_update
  AFTER UPDATE ON t_mrt_access_services
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_access_services_update()
/
DROP TRIGGER tr_t_mrt_vers_impacts_before_update ON t_mrt_vers_impacts CASCADE;
--/
CREATE TRIGGER tr_t_mrt_vers_impacts_before_update
  BEFORE UPDATE ON t_mrt_vers_impacts
  FOR EACH ROW
EXECUTE PROCEDURE update_mrvi_last_modification_time_function()
/
DROP TRIGGER tr_t_mrt_vers_impacts_ins ON t_mrt_vers_impacts CASCADE;
--/
CREATE TRIGGER tr_t_mrt_vers_impacts_ins
  BEFORE INSERT ON t_mrt_vers_impacts
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_vers_impacts_ins()
/
DROP TRIGGER tr_t_mrt_vers_impacts_upd_currentstate ON t_mrt_vers_impacts CASCADE;
--/
CREATE TRIGGER tr_t_mrt_vers_impacts_upd_currentstate
  BEFORE UPDATE ON t_mrt_vers_impacts
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_mrt_vers_impacts_upd_currentstate()
/
DROP TRIGGER tr_t_net_resource_rels_before_update ON t_net_resource_rels CASCADE;
--/
CREATE TRIGGER tr_t_net_resource_rels_before_update
  BEFORE UPDATE ON t_net_resource_rels
  FOR EACH ROW
EXECUTE PROCEDURE update_nrre_last_modification_time_function()
/
DROP TRIGGER tr_t_net_resource_rels_ins_before ON t_net_resource_rels CASCADE;
--/
CREATE TRIGGER tr_t_net_resource_rels_ins_before
  BEFORE INSERT ON t_net_resource_rels
  FOR EACH ROW
EXECUTE PROCEDURE update_nrre_creation_time_function()
/
DROP TRIGGER tr_t_port_groups_before_update ON t_port_groups CASCADE;
--/
CREATE TRIGGER tr_t_port_groups_before_update
  BEFORE UPDATE ON t_port_groups
  FOR EACH ROW
EXECUTE PROCEDURE update_pogr_last_modification_time_function()
/
DROP TRIGGER tr_t_port_groups_ins_before ON t_port_groups CASCADE;
--/
CREATE TRIGGER tr_t_port_groups_ins_before
  BEFORE INSERT ON t_port_groups
  FOR EACH ROW
EXECUTE PROCEDURE update_pogr_creation_time_function()
/
DROP TRIGGER tr_t_ports_before_update ON t_ports CASCADE;
--/
CREATE TRIGGER tr_t_ports_before_update
  BEFORE UPDATE ON t_ports
  FOR EACH ROW
EXECUTE PROCEDURE update_port_last_modification_time_function()
/
DROP TRIGGER tr_t_ports_del ON t_ports CASCADE;
--/
CREATE TRIGGER tr_t_ports_del
  BEFORE DELETE ON t_ports
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_ports_del()
/
DROP TRIGGER tr_t_ports_ins ON t_ports CASCADE;
--/
CREATE TRIGGER tr_t_ports_ins
  BEFORE INSERT ON t_ports
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_ports_ins()
/
DROP TRIGGER tr_t_ports_upd_aralianamepcpinterface ON t_ports CASCADE;
--/
CREATE TRIGGER tr_t_ports_upd_aralianamepcpinterface
  BEFORE UPDATE ON t_ports
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_ports_upd_aralianamepcpinterface()
/
DROP TRIGGER tr_t_ports_upd_pcpfunc ON t_ports CASCADE;
--/
CREATE TRIGGER tr_t_ports_upd_pcpfunc
  BEFORE UPDATE ON t_ports
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_ports_upd_pcpfunc()
/
DROP TRIGGER tr_t_ports_upd_usagecounter ON t_ports CASCADE;
--/
CREATE TRIGGER tr_t_ports_upd_usagecounter
  BEFORE UPDATE ON t_ports
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_ports_upd_usagecounter()
/
DROP TRIGGER tr_t_res_prod_controlables_before_update ON t_res_prod_controlables CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_controlables_before_update
  BEFORE UPDATE ON t_res_prod_controlables
  FOR EACH ROW
EXECUTE PROCEDURE update_rpct_last_modification_time_function()
/
DROP TRIGGER tr_t_res_prod_controlables_del ON t_res_prod_controlables CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_controlables_del
  BEFORE DELETE ON t_res_prod_controlables
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_res_prod_controlables_del()
/
DROP TRIGGER tr_t_res_prod_controlables_ins ON t_res_prod_controlables CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_controlables_ins
  AFTER INSERT ON t_res_prod_controlables
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_res_prod_controlables_ins()
/
DROP TRIGGER tr_t_res_prod_controlables_ins_before ON t_res_prod_controlables CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_controlables_ins_before
  BEFORE INSERT ON t_res_prod_controlables
  FOR EACH ROW
EXECUTE PROCEDURE update_rpct_creation_time_function()
/
DROP TRIGGER tr_t_res_prod_controlables_upd_role ON t_res_prod_controlables CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_controlables_upd_role
  BEFORE UPDATE ON t_res_prod_controlables
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_res_prod_controlables_upd_role()
/
DROP TRIGGER tr_t_res_prod_controlables_update ON t_res_prod_controlables CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_controlables_update
  AFTER UPDATE ON t_res_prod_controlables
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_res_prod_controlables_update()
/
DROP TRIGGER tr_t_res_prod_roles_before_update ON t_res_prod_roles CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_roles_before_update
  BEFORE UPDATE ON t_res_prod_roles
  FOR EACH ROW
EXECUTE PROCEDURE update_rpro_last_modification_time_function()
/
DROP TRIGGER tr_t_res_prod_roles_del ON t_res_prod_roles CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_roles_del
  BEFORE DELETE ON t_res_prod_roles
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_res_prod_roles_del()
/
DROP TRIGGER tr_t_res_prod_roles_ins ON t_res_prod_roles CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_roles_ins
  BEFORE INSERT ON t_res_prod_roles
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_res_prod_roles_ins()
/
DROP TRIGGER tr_t_res_prod_roles_upd ON t_res_prod_roles CASCADE;
--/
CREATE TRIGGER tr_t_res_prod_roles_upd
  BEFORE UPDATE ON t_res_prod_roles
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_res_prod_roles_upd()
/
DROP TRIGGER tr_t_resource_usages_before_update ON t_resource_usages CASCADE;
--/
CREATE TRIGGER tr_t_resource_usages_before_update
  BEFORE UPDATE ON t_resource_usages
  FOR EACH ROW
EXECUTE PROCEDURE update_rsus_last_modification_time_function()
/
DROP TRIGGER tr_t_resource_usages_del ON t_resource_usages CASCADE;
--/
CREATE TRIGGER tr_t_resource_usages_del
  AFTER DELETE ON t_resource_usages
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_resource_usages_del()
/
DROP TRIGGER tr_t_resource_usages_ins ON t_resource_usages CASCADE;
--/
CREATE TRIGGER tr_t_resource_usages_ins
  AFTER INSERT ON t_resource_usages
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_resource_usages_ins()
/
DROP TRIGGER tr_t_resource_usages_ins_before ON t_resource_usages CASCADE;
--/
CREATE TRIGGER tr_t_resource_usages_ins_before
  BEFORE INSERT ON t_resource_usages
  FOR EACH ROW
EXECUTE PROCEDURE update_rsus_creation_time_function()
/
DROP TRIGGER tr_t_resource_usages_upd ON t_resource_usages CASCADE;
--/
CREATE TRIGGER tr_t_resource_usages_upd
  AFTER UPDATE ON t_resource_usages
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_resource_usages_upd()
/
DROP TRIGGER tr_t_shelfs_before_update ON t_shelfs CASCADE;
--/
CREATE TRIGGER tr_t_shelfs_before_update
  BEFORE UPDATE ON t_shelfs
  FOR EACH ROW
EXECUTE PROCEDURE update_shlf_last_modification_time_function()
/
DROP TRIGGER tr_t_shelfs_del ON t_shelfs CASCADE;
--/
CREATE TRIGGER tr_t_shelfs_del
  BEFORE DELETE ON t_shelfs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_shelfs_del()
/
DROP TRIGGER tr_t_shelfs_ins ON t_shelfs CASCADE;
--/
CREATE TRIGGER tr_t_shelfs_ins
  AFTER INSERT ON t_shelfs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_shelfs_ins()
/
DROP TRIGGER tr_t_shelfs_ins_before ON t_shelfs CASCADE;
--/
CREATE TRIGGER tr_t_shelfs_ins_before
  BEFORE INSERT ON t_shelfs
  FOR EACH ROW
EXECUTE PROCEDURE update_shlf_creation_time_function()
/
DROP TRIGGER tr_t_shelfs_upd ON t_shelfs CASCADE;
--/
CREATE TRIGGER tr_t_shelfs_upd
  BEFORE UPDATE ON t_shelfs
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_shelfs_upd()
/
DROP TRIGGER tr_t_slots_before_update ON t_slots CASCADE;
--/
CREATE TRIGGER tr_t_slots_before_update
  BEFORE UPDATE ON t_slots
  FOR EACH ROW
EXECUTE PROCEDURE update_slot_last_modification_time_function()
/
DROP TRIGGER tr_t_slots_ins_before ON t_slots CASCADE;
--/
CREATE TRIGGER tr_t_slots_ins_before
  BEFORE INSERT ON t_slots
  FOR EACH ROW
EXECUTE PROCEDURE update_slot_creation_time_function()
/
DROP TRIGGER tr_t_slots_upd_supportedequipsize ON t_slots CASCADE;
--/
CREATE TRIGGER tr_t_slots_upd_supportedequipsize
  BEFORE UPDATE ON t_slots
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_slots_upd_supportedequipsize()
/
DROP TRIGGER tr_t_stripes_before_update ON t_stripes CASCADE;
--/
CREATE TRIGGER tr_t_stripes_before_update
  BEFORE UPDATE ON t_stripes
  FOR EACH ROW
EXECUTE PROCEDURE update_strp_last_modification_time_function()
/
DROP TRIGGER tr_t_stripes_ins_before ON t_stripes CASCADE;
--/
CREATE TRIGGER tr_t_stripes_ins_before
  BEFORE INSERT ON t_stripes
  FOR EACH ROW
EXECUTE PROCEDURE update_strp_creation_time_function()
/
DROP TRIGGER tr_t_stripes_upd_name ON t_stripes CASCADE;
--/
CREATE TRIGGER tr_t_stripes_upd_name
  AFTER UPDATE ON t_stripes
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_stripes_upd_name()
/
DROP TRIGGER tr_t_tr_assignments_del ON t_tr_assignments CASCADE;
--/
CREATE TRIGGER tr_t_tr_assignments_del
  BEFORE DELETE ON t_tr_assignments
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_tr_assignments_del()
/
DROP TRIGGER tr_t_vc_lock_ranges_before_update ON t_vc_lock_ranges CASCADE;
--/
CREATE TRIGGER tr_t_vc_lock_ranges_before_update
  BEFORE UPDATE ON t_vc_lock_ranges
  FOR EACH ROW
EXECUTE PROCEDURE update_vckr_last_modification_time_function()
/
DROP TRIGGER tr_t_vc_lock_ranges_del ON t_vc_lock_ranges CASCADE;
--/
CREATE TRIGGER tr_t_vc_lock_ranges_del
  AFTER DELETE ON t_vc_lock_ranges
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_vc_lock_ranges_del()
/
DROP TRIGGER tr_t_vc_lock_ranges_ins ON t_vc_lock_ranges CASCADE;
--/
CREATE TRIGGER tr_t_vc_lock_ranges_ins
  AFTER INSERT ON t_vc_lock_ranges
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_vc_lock_ranges_ins()
/
DROP TRIGGER tr_t_vc_lock_ranges_ins_before ON t_vc_lock_ranges CASCADE;
--/
CREATE TRIGGER tr_t_vc_lock_ranges_ins_before
  BEFORE INSERT ON t_vc_lock_ranges
  FOR EACH ROW
EXECUTE PROCEDURE update_vckr_creation_time_function()
/
DROP TRIGGER tr_t_vc_lock_ranges_upd ON t_vc_lock_ranges CASCADE;
--/
CREATE TRIGGER tr_t_vc_lock_ranges_upd
  AFTER UPDATE ON t_vc_lock_ranges
  FOR EACH ROW
EXECUTE PROCEDURE sp_t_vc_lock_ranges_upd()
/
