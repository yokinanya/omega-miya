from typing import List, Optional
from datetime import date, datetime
from dataclasses import dataclass
from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import User, UserFavorability, UserSignIn, Skill, UserSkill, Vacation
from .skill import DBSkill
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBUser(object):
    def __init__(self, user_id: int):
        self.qq = user_id

    @dataclass
    class DateListResult(Result.AnyResult):
        result: List[date]

        def __repr__(self):
            return f'<DateListResult(error={self.error}, info={self.info}, result={self.result})>'

    async def id(self) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(User.id).where(User.qq == self.qq)
                    )
                    user_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=user_table_id)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    async def nickname(self) -> Result.TextResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(User.nickname).where(User.qq == self.qq)
                    )
                    user_nickname = session_result.scalar_one()
                    result = Result.TextResult(error=False, info='Success', result=user_nickname)
                except NoResultFound:
                    result = Result.TextResult(error=True, info='NoResultFound', result='')
                except MultipleResultsFound:
                    result = Result.TextResult(error=True, info='MultipleResultsFound', result='')
                except Exception as e:
                    result = Result.TextResult(error=True, info=repr(e), result='')
        return result

    async def add(self, nickname: str, aliasname: str = None) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        # ???????????????????????????????????????
                        session_result = await session.execute(
                            select(User).where(User.qq == self.qq)
                        )
                        exist_user = session_result.scalar_one()
                        if exist_user.nickname == nickname:
                            result = Result.IntResult(error=False, info='Nickname not change', result=0)
                        else:
                            exist_user.nickname = nickname
                            exist_user.aliasname = aliasname
                            exist_user.updated_at = datetime.now()
                            result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        # ???????????????????????????????????????
                        new_user = User(qq=self.qq, nickname=nickname, aliasname=aliasname, created_at=datetime.now())
                        session.add(new_user)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self) -> Result.IntResult:
        id_result = await self.id()
        if id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # ????????????????????????
                    session_result = await session.execute(
                        select(User).where(User.qq == self.qq)
                    )
                    exist_user = session_result.scalar_one()
                    await session.delete(exist_user)
                await session.commit()
                result = Result.IntResult(error=False, info='Success Delete', result=0)
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def skill_list(self) -> Result.ListResult:
        id_result = await self.id()
        if id_result.error:
            return Result.ListResult(error=True, info='User not exist', result=[])

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Skill.name, UserSkill.skill_level).
                        join(UserSkill).
                        where(Skill.id == UserSkill.skill_id).
                        where(UserSkill.user_id == id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def skill_add(self, skill: DBSkill, skill_level: int) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        skill_id_result = await skill.id()
        if skill_id_result.error:
            return Result.IntResult(error=True, info='Skill not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # ????????????????????????
                    try:
                        # ????????????, ????????????
                        session_result = await session.execute(
                            select(UserSkill).
                            where(UserSkill.skill_id == skill_id_result.result).
                            where(UserSkill.user_id == user_id_result.result)
                        )
                        exist_skill = session_result.scalar_one()
                        exist_skill.skill_level = skill_level
                        exist_skill.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_skill = UserSkill(user_id=user_id_result.result, skill_id=skill_id_result.result,
                                              skill_level=skill_level, created_at=datetime.now())
                        session.add(new_skill)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def skill_del(self, skill: DBSkill) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        skill_id_result = await skill.id()
        if skill_id_result.error:
            return Result.IntResult(error=True, info='Skill not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserSkill).
                        where(UserSkill.skill_id == skill_id_result.result).
                        where(UserSkill.user_id == user_id_result.result)
                    )
                    exist_skill = session_result.scalar_one()
                    await session.delete(exist_skill)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def skill_clear(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserSkill).where(UserSkill.user_id == user_id_result.result)
                    )
                    for exist_skill in session_result.scalars().all():
                        await session.delete(exist_skill)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def status(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Vacation.status).where(Vacation.user_id == user_id_result.result)
                    )
                    res = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def vacation_status(self) -> Result.ListResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.ListResult(error=True, info='User not exist', result=[-1, None])

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Vacation.status, Vacation.stop_at).
                        where(Vacation.user_id == user_id_result.result)
                    )
                    res = session_result.one()
                    result = Result.ListResult(error=False, info='Success', result=[res[0], res[1]])
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[-1, None])
        return result

    async def status_set(self, status: int) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Vacation).where(Vacation.user_id == user_id_result.result)
                        )
                        exist_status = session_result.scalar_one()
                        exist_status.status = status
                        exist_status.stop_at = None
                        exist_status.reason = None
                        exist_status.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_status = Vacation(user_id=user_id_result.result, status=status, created_at=datetime.now())
                        session.add(new_status)
                        result = Result.IntResult(error=False, info='Success set', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def vacation_set(self, stop_time: datetime, reason: str = None) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Vacation).where(Vacation.user_id == user_id_result.result)
                        )
                        exist_status = session_result.scalar_one()
                        exist_status.status = 1
                        exist_status.stop_at = stop_time
                        exist_status.reason = reason
                        exist_status.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_status = Vacation(user_id=user_id_result.result, status=1,
                                              stop_at=stop_time, reason=reason, created_at=datetime.now())
                        session.add(new_status)
                        result = Result.IntResult(error=False, info='Success set', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def status_del(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Vacation).where(Vacation.user_id == user_id_result.result)
                    )
                    exist_status = session_result.scalar_one()
                    await session.delete(exist_status)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def sign_in(
            self,
            *,
            sign_in_info: Optional[str] = 'Normal sign in',
            date_: Optional[datetime] = None) -> Result.IntResult:
        """
        ??????
        :param sign_in_info: ????????????
        :param date_: ??????????????????
        :return: IntResult
            1: ?????????
            0: ????????????
            -1: ??????
        """
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        if isinstance(date_, datetime):
            date_now = date_.date()
        else:
            date_now = datetime.now().date()

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(UserSignIn).
                            where(UserSignIn.user_id == user_id_result.result).
                            where(UserSignIn.sign_in_date == date_now)
                        )
                        # ??????????????????
                        exist_sign_in = session_result.scalar_one()
                        exist_sign_in.sign_in_info = 'Duplicate sign in'
                        exist_sign_in.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=1)
                    except NoResultFound:
                        sign_in = UserSignIn(user_id=user_id_result.result, sign_in_date=date_now,
                                             sign_in_info=sign_in_info, created_at=datetime.now())
                        session.add(sign_in)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def sign_in_statistics(self) -> DateListResult:
        """
        ????????????????????????
        :return: Result: List[sign_in_date]
        """
        user_id_result = await self.id()
        if user_id_result.error:
            return self.DateListResult(error=True, info='User not exist', result=[])

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(UserSignIn.sign_in_date).
                        where(UserSignIn.user_id == user_id_result.result)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = self.DateListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = self.DateListResult(error=True, info=repr(e), result=[])
        return result

    async def sign_in_continuous_days(self) -> Result.IntResult:
        """
        ?????????????????????????????????????????????
        """
        sign_in_statistics_result = await self.sign_in_statistics()
        if sign_in_statistics_result.error:
            return Result.IntResult(error=True, info=sign_in_statistics_result.info, result=-1)

        # ??????????????????
        if not sign_in_statistics_result.result:
            return Result.IntResult(error=False, info='Success with sign in not found', result=0)

        date_now_ordinal = datetime.now().date().toordinal()

        # ?????????????????????????????????????????????????????????
        all_sign_in_list = list(set([x.toordinal() for x in sign_in_statistics_result.result]))
        # ???????????????????????????
        all_sign_in_list.sort(reverse=True)

        # ???????????????????????????????????????????????????, ????????????????????????, ??????????????????0
        if date_now_ordinal != all_sign_in_list[0]:
            return Result.IntResult(error=False, info='Success with not sign in today', result=0)

        # ??????????????????(???????????????????????????), ???????????????????????????????????????????????????, ????????????????????????
        for index, value in enumerate(all_sign_in_list):
            if index != date_now_ordinal - value:
                return Result.IntResult(error=False, info='Success with found interrupt', result=index)
        else:
            # ??????????????????????????????????????????????????????
            return Result.IntResult(error=False, info='Success with all continuous', result=len(all_sign_in_list))

    async def sign_in_last_missing_day(self) -> Result.IntResult:
        """
        ??????????????????????????????, ?????? ordinal datetime
        """
        sign_in_statistics_result = await self.sign_in_statistics()
        if sign_in_statistics_result.error:
            return Result.IntResult(error=True, info=sign_in_statistics_result.info, result=-1)

        date_now_ordinal = datetime.now().date().toordinal()

        # ??????????????????, ??????????????????????????????
        if not sign_in_statistics_result.result:
            return Result.IntResult(error=False, info='Success with today not sign in', result=date_now_ordinal)

        # ????????????????????????????????????
        # ?????????????????????????????????????????????????????????
        all_sign_in_list = list(set([x.toordinal() for x in sign_in_statistics_result.result]))
        # ???????????????????????????
        all_sign_in_list.sort(reverse=True)

        # ???????????????????????????????????????????????????, ????????????????????????, ??????????????????
        if date_now_ordinal != all_sign_in_list[0]:
            return Result.IntResult(error=False, info='Success with not sign in today', result=date_now_ordinal)

        # ??????????????????(???????????????????????????), ???????????????????????????????????????????????????, ????????????????????????
        # ????????????????????????????????????????????? ordinal datetime
        for index, value in enumerate(all_sign_in_list):
            if index != date_now_ordinal - value:
                return Result.IntResult(error=False, info='Success with found interrupt',
                                        result=(all_sign_in_list[index - 1] - 1))
        else:
            # ??????????????????????????????????????????????????????????????????????????????
            return Result.IntResult(error=False, info='Success with all continuous',
                                    result=(date_now_ordinal - len(all_sign_in_list)))

    async def sign_in_check_today(self) -> Result.IntResult:
        """
        ??????????????????????????????
        :return: IntResult
            1: ?????????
            0: ?????????
            -1: ??????
        """
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        today = date.today()
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(UserSignIn.sign_in_date).
                        where(UserSignIn.sign_in_date == today).
                        where(UserSignIn.user_id == user_id_result.result)
                    )
                    res = session_result.scalar_one()
                    result = Result.IntResult(error=False, info=f'Checked today: {res}', result=1)
                except NoResultFound:
                    result = Result.IntResult(error=False, info='Not Sign in today', result=0)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def favorability_status(self) -> Result.TupleResult:
        """
        ?????????????????????
        :return: Result:
        Tuple[status: str, mood: float, favorability: float, energy: float, currency: float, response_threshold: float]
        """
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.TupleResult(error=True, info='User not exist', result=())

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(UserFavorability.status,
                               UserFavorability.mood,
                               UserFavorability.favorability,
                               UserFavorability.energy,
                               UserFavorability.currency,
                               UserFavorability.response_threshold).
                        where(UserFavorability.user_id == user_id_result.result)
                    )
                    res = session_result.one()
                    result = Result.TupleResult(error=False, info='Success', result=res)
                except NoResultFound:
                    result = Result.TupleResult(error=True, info='NoResultFound', result=())
                except MultipleResultsFound:
                    result = Result.TupleResult(error=True, info='MultipleResultsFound', result=())
                except Exception as e:
                    result = Result.TupleResult(error=True, info=repr(e), result=())
        return result

    async def favorability_reset(
            self,
            *,
            status: str = 'normal',
            mood: float = 0,
            favorability: float = 0,
            energy: float = 0,
            currency: float = 0,
            response_threshold: float = 0
    ) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(UserFavorability).
                            where(UserFavorability.user_id == user_id_result.result)
                        )
                        # ???????????????????????????
                        exist_favorability = session_result.scalar_one()
                        exist_favorability.status = status
                        exist_favorability.mood = mood
                        exist_favorability.favorability = favorability
                        exist_favorability.energy = energy
                        exist_favorability.currency = currency
                        exist_favorability.response_threshold = response_threshold
                        exist_favorability.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        favorability = UserFavorability(
                            user_id=user_id_result.result, status=status, mood=mood, favorability=favorability,
                            energy=energy, currency=currency, response_threshold=response_threshold,
                            created_at=datetime.now())
                        session.add(favorability)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def favorability_add(
            self,
            *,
            status: Optional[str] = None,
            mood: Optional[float] = None,
            favorability: Optional[float] = None,
            energy: Optional[float] = None,
            currency: Optional[float] = None,
            response_threshold: Optional[float] = None
    ) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserFavorability).
                        where(UserFavorability.user_id == user_id_result.result)
                    )
                    # ???????????????????????????
                    exist_favorability = session_result.scalar_one()
                    if status:
                        exist_favorability.status = status
                    if mood:
                        exist_favorability.mood += mood
                    if favorability:
                        exist_favorability.favorability += favorability
                    if energy:
                        exist_favorability.energy += energy
                    if currency:
                        exist_favorability.currency += currency
                    if response_threshold:
                        exist_favorability.response_threshold += response_threshold
                    exist_favorability.updated_at = datetime.now()
                    result = Result.IntResult(error=False, info='Success upgraded', result=0)
                await session.commit()
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
